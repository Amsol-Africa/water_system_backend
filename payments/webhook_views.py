#==============================================
## File: payments/webhook_views.py
# =============================================
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.utils import timezone
from django.db import transaction
import logging
from decimal import Decimal, InvalidOperation

from .models import PaymentNotification
from clients.models import Client
from meters.models import Meter, MeterAssignment
from customers.models import Customer
from tokens.services import vend_and_create_token_for_payment
from tokens.models import Token
from core.sms_service import SMSService

logger = logging.getLogger(__name__)


def _extract_mpesa_fields(payload):
    """
    C2B payload example you showed:
    {
      "MSISDN": "...",
      "TransID": "...",
      "TransTime": "...",
      "TransAmount": "30.00",
      "BillRefNumber": "...",
      "BusinessShortCode": "600999",
      ...
    }
    """
    trans_id = payload.get("TransID") or payload.get("TransactionID")
    amount = payload.get("TransAmount") or payload.get("Amount")

    paybill = payload.get("BusinessShortCode") or payload.get("ShortCode")

    # Some payloads use ReceiverPartyPublicName like "4003047 - AMSOL WATER"
    if not paybill:
        rppn = payload.get("ReceiverPartyPublicName")
        if rppn and isinstance(rppn, str):
            paybill = rppn.split(" ")[0].strip()  # "4003047"

    account_number = payload.get("BillRefNumber") or payload.get("AccountReference") or payload.get("AccountNumber")

    phone = payload.get("MSISDN") or payload.get("CustomerMSISDN") or payload.get("PhoneNumber")

    return {
        "mpesa_transaction_id": str(trans_id) if trans_id else None,
        "amount": amount,
        "paybill": str(paybill) if paybill else None,
        "account_number": str(account_number) if account_number else None,
        "phone": str(phone) if phone else None,
    }


class MPesaC2BValidationView(APIView):
    """
    Safaricom calls this BEFORE confirmation.
    Keep it FAST. Just accept/reject.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        payload = request.data
        logger.info(f"M-Pesa C2B VALIDATION received: {payload}")

        fields = _extract_mpesa_fields(payload)
        paybill = fields["paybill"]
        account_number = fields["account_number"]

        # Optional validations (recommended):
        # - Paybill exists as a configured Client
        # - Meter exists
        if not paybill or not account_number:
            return Response({"ResultCode": 1, "ResultDesc": "Missing required fields"}, status=status.HTTP_200_OK)

        client = Client.objects.filter(paybill_number=str(paybill)).first()
        if not client:
            return Response({"ResultCode": 1, "ResultDesc": "Unknown Paybill"}, status=status.HTTP_200_OK)

        meter = Meter.objects.filter(meter_id=str(account_number), client=client).first()
        if not meter:
            return Response({"ResultCode": 1, "ResultDesc": "Unknown Meter"}, status=status.HTTP_200_OK)

        return Response({"ResultCode": 0, "ResultDesc": "Accepted"}, status=status.HTTP_200_OK)


class MPesaC2BConfirmationView(APIView):
    """
    Safaricom calls this AFTER payment has been completed.
    This is where you create PaymentNotification + vend token + SMS.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        payload = request.data
        logger.info(f"M-Pesa C2B CONFIRMATION received: {payload}")

        fields = _extract_mpesa_fields(payload)

        tx_id = fields["mpesa_transaction_id"]
        amount = fields["amount"]
        paybill = fields["paybill"]
        account_number = fields["account_number"]
        phone = fields["phone"]

        if not tx_id or not amount or not paybill or not account_number or not phone:
            logger.error("M-Pesa confirmation missing required fields")
            return Response({"ResultCode": 1, "ResultDesc": "Missing required fields"}, status=status.HTTP_200_OK)

        # Idempotency
        if PaymentNotification.objects.filter(mpesa_transaction_id=tx_id).exists():
            return Response({"ResultCode": 0, "ResultDesc": "Already processed"}, status=status.HTTP_200_OK)

        try:
            amount_decimal = Decimal(str(amount))
        except InvalidOperation:
            logger.error(f"Invalid amount: {amount}")
            return Response({"ResultCode": 1, "ResultDesc": "Invalid amount"}, status=status.HTTP_200_OK)

        # Client must match paybill
        client = Client.objects.filter(paybill_number=str(paybill)).first()

        # Meter should belong to client (important in multi-tenant)
        meter = None
        if client:
            meter = Meter.objects.filter(meter_id=str(account_number), client=client).first()
        if not meter:
            meter = Meter.objects.filter(meter_id=str(account_number)).first()  # fallback (optional)

        # Customer resolution
        customer = None
        if client:
            customer = Customer.objects.filter(client=client, phone=str(phone)).first()

        if not customer and meter:
            assignment = (
                MeterAssignment.objects
                .filter(meter=meter, is_active=True)
                .select_related("customer")
                .first()
            )
            if assignment:
                customer = assignment.customer

        sms_service = SMSService()

        with transaction.atomic():
            notification = PaymentNotification.objects.create(
                mpesa_transaction_id=tx_id,
                amount=amount_decimal,
                paybill=str(paybill),
                account_number=str(account_number),
                phone=str(phone),
                client=client,
                customer=customer,
                status=PaymentNotification.PENDING,
                raw_payload=payload,
            )

            if not client:
                notification.status = PaymentNotification.FAILED
                notification.error_message = "Client not found for paybill"
                notification.processed_at = timezone.now()
                notification.save(update_fields=["status", "error_message", "processed_at"])
                return Response({"ResultCode": 0, "ResultDesc": "Client not configured"}, status=status.HTTP_200_OK)

            if not meter:
                notification.status = PaymentNotification.FAILED
                notification.error_message = "Meter not found"
                notification.processed_at = timezone.now()
                notification.save(update_fields=["status", "error_message", "processed_at"])
                return Response({"ResultCode": 0, "ResultDesc": "Meter not found"}, status=status.HTTP_200_OK)

            if not customer:
                notification.status = PaymentNotification.FAILED
                notification.error_message = "Customer not found"
                notification.processed_at = timezone.now()
                notification.save(update_fields=["status", "error_message", "processed_at"])
                return Response({"ResultCode": 0, "ResultDesc": "Customer not found"}, status=status.HTTP_200_OK)

            success, token, error = vend_and_create_token_for_payment(
                meter=meter,
                customer=customer,
                amount=amount_decimal,
                is_vend_by_unit=False,
                payment=notification,
                idempotency_key=tx_id,
            )

            if not success or not token:
                notification.status = PaymentNotification.FAILED
                notification.error_message = error or "Vending failed"
                notification.processed_at = timezone.now()
                notification.save(update_fields=["status", "error_message", "processed_at"])
                return Response({"ResultCode": 0, "ResultDesc": "Vending failed"}, status=status.HTTP_200_OK)

            notification.status = PaymentNotification.VERIFIED
            notification.processed_at = timezone.now()
            notification.save(update_fields=["status", "processed_at"])

            sms_ok = sms_service.send_template(
                to_number=customer.phone,
                template_name="token_issued",
                context={
                    "meter_id": meter.meter_id,
                    "token": token.token_value,
                    "amount": amount_decimal,
                },
            )

            if sms_ok and token.status != Token.DELIVERED:
                token.status = Token.DELIVERED
                token.delivered_at = timezone.now()
                token.save(update_fields=["status", "delivered_at"])

        return Response({"ResultCode": 0, "ResultDesc": "Success"}, status=status.HTTP_200_OK)
