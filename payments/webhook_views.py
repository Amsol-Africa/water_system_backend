# ============================================
# payments/webhook_views.py  
# ============================================
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
    Helper to normalize common M-Pesa C2B/STK callback fields.
    Adjust keys to your actual Daraja payload.
    """

    trans_id = (
        payload.get("TransID")
        or payload.get("TransactionID")
        or payload.get("CheckoutRequestID")
    )
    amount = payload.get("TransAmount") or payload.get("Amount")
    paybill = (
        payload.get("BusinessShortCode")
        or payload.get("ShortCode")
        or payload.get("ReceiverPartyPublicName")
    )
    account_number = (
        payload.get("BillRefNumber")
        or payload.get("AccountReference")
        or payload.get("AccountNumber")
    )
    phone = (
        payload.get("MSISDN")
        or payload.get("CustomerMSISDN")
        or payload.get("PhoneNumber")
    )

    return {
        "mpesa_transaction_id": str(trans_id) if trans_id else None,
        "amount": amount,
        "paybill": str(paybill) if paybill else None,
        "account_number": str(account_number) if account_number else None,
        "phone": str(phone) if phone else None,
    }


class MPesaWebhookView(APIView):
    """M-Pesa webhook receiver (C2B / STK callback)"""
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Receive M-Pesa payment notifications and auto-vend tokens.

        Flow:
        - Parse payload
        - Create PaymentNotification
        - Resolve Client (by paybill)
        - Resolve Meter (by account_number)
        - Resolve Customer (by phone / meter assignment)
        - Call Stronpower vending
        - Create Token + VendingRequest
        - Mark PaymentNotification VERIFIED
        - Send SMS with token
        """
        payload = request.data
        logger.info(f"M-Pesa webhook received: {payload}")

        fields = _extract_mpesa_fields(payload)

        tx_id = fields["mpesa_transaction_id"]
        amount = fields["amount"]
        paybill = fields["paybill"]
        account_number = fields["account_number"]
        phone = fields["phone"]

        if not tx_id or not amount or not paybill or not account_number or not phone:
            logger.error("M-Pesa webhook missing required fields")
            return Response(
                {"ResultCode": 1, "ResultDesc": "Missing required fields"},
                status=status.HTTP_200_OK,
            )

        # Idempotency: if we already processed this tx, just ACK to M-Pesa
        existing = PaymentNotification.objects.filter(
            mpesa_transaction_id=tx_id
        ).first()
        if existing:
            logger.info(
                f"M-Pesa tx {tx_id} already processed with status {existing.status}"
            )
            return Response(
                {"ResultCode": 0, "ResultDesc": "Already processed"},
                status=status.HTTP_200_OK,
            )

        # Convert amount to Decimal safely
        try:
            amount_decimal = Decimal(str(amount))
        except InvalidOperation:
            logger.error(f"Invalid amount in M-Pesa payload: {amount}")
            return Response(
                {"ResultCode": 1, "ResultDesc": "Invalid amount"},
                status=status.HTTP_200_OK,
            )

        # --- Resolve client from paybill ---
        client = Client.objects.filter(paybill_number=str(paybill)).first()

        # --- Resolve meter from account_number (meter_id) ---
        meter = Meter.objects.filter(meter_id=str(account_number)).first()

        # --- Resolve customer ---
        customer = None
        if client:
            customer = Customer.objects.filter(
                client=client,
                phone=phone,
            ).first()

        if not customer and meter:
            assignment = (
                MeterAssignment.objects.filter(
                    meter=meter,
                    is_active=True,
                )
                .select_related("customer")
                .first()
            )
            if assignment:
                customer = assignment.customer

        sms_service = SMSService()

        # Create PaymentNotification and then vend
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

            # Validation of client / meter / customer
            if not client:
                notification.status = PaymentNotification.FAILED
                notification.error_message = "Client not found for paybill"
                notification.processed_at = timezone.now()
                notification.save(
                    update_fields=["status", "error_message", "processed_at"]
                )
                logger.error(f"Client not found for paybill {paybill}")
                return Response(
                    {"ResultCode": 0, "ResultDesc": "Client not configured"},
                    status=status.HTTP_200_OK,
                )

            if not meter:
                notification.status = PaymentNotification.FAILED
                notification.error_message = "Meter not found for account number"
                notification.processed_at = timezone.now()
                notification.save(
                    update_fields=["status", "error_message", "processed_at"]
                )
                logger.error(
                    f"Meter not found for account/account_number {account_number}"
                )
                return Response(
                    {"ResultCode": 0, "ResultDesc": "Meter not found"},
                    status=status.HTTP_200_OK,
                )

            if not customer:
                notification.status = PaymentNotification.FAILED
                notification.error_message = "Customer not found for phone/meter"
                notification.processed_at = timezone.now()
                notification.save(
                    update_fields=["status", "error_message", "processed_at"]
                )
                logger.error(
                    f"Customer not found for phone {phone} / meter {meter.meter_id}"
                )
                return Response(
                    {"ResultCode": 0, "ResultDesc": "Customer not found"},
                    status=status.HTTP_200_OK,
                )

            # --- Stronpower vending + Token + VendingRequest (idempotent) ---
            success, token, error = vend_and_create_token_for_payment(
                meter=meter,
                customer=customer,
                amount=amount_decimal,
                is_vend_by_unit=False,  # vending by money (KES)
                payment=notification,
                idempotency_key=tx_id,
            )

            if not success or not token:
                notification.status = PaymentNotification.FAILED
                notification.error_message = error or "Vending failed"
                notification.processed_at = timezone.now()
                notification.save(
                    update_fields=["status", "error_message", "processed_at"]
                )
                logger.error(f"Stronpower vending failed for tx {tx_id}: {error}")
                return Response(
                    {"ResultCode": 0, "ResultDesc": "Vending failed"},
                    status=status.HTTP_200_OK,
                )

            # Mark payment as VERIFIED
            notification.status = PaymentNotification.VERIFIED
            notification.processed_at = timezone.now()
            notification.save(update_fields=["status", "processed_at"])

            # Send SMS
            sms_ok = sms_service.send_template(
                to_number=customer.phone,
                template_name="token_issued",
                context={
                    "meter_id": meter.meter_id,
                    "token": token.token_value,
                    "amount": amount_decimal,
                },
            )

            # Optionally mark token as DELIVERED if SMS success
            if sms_ok and token.status != Token.DELIVERED:
                token.status = Token.DELIVERED
                token.delivered_at = timezone.now()
                token.save(update_fields=["status", "delivered_at"])

            logger.info(
                f"Token {token.token_value} issued for tx {tx_id}, "
                f"sent to {customer.phone} (SMS ok={sms_ok})"
            )

        # ACK to M-Pesa
        return Response(
            {"ResultCode": 0, "ResultDesc": "Success"},
            status=status.HTTP_200_OK,
        )


class MPesaCallbackView(APIView):
    """M-Pesa callback handler (if you use a separate callback URL)"""
    permission_classes = [AllowAny]

    def post(self, request):
        logger.info(f"M-Pesa callback received: {request.data}")
        return Response(
            {"ResultCode": 0, "ResultDesc": "Callback received"},
            status=status.HTTP_200_OK,
        )
