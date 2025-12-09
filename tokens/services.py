# ============================================
# FILE: tokens/services.py  
# ============================================
from __future__ import annotations

from typing import Tuple, Optional, Dict, Any
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.db import transaction

from .models import Token, VendingRequest
from meters.models import Meter
from customers.models import Customer
from payments.models import PaymentNotification
from integrations.stronpower_service import StronpowerService
from core.sms_service import SMSService


def vend_and_create_token_for_payment(
    *,
    meter: Meter,
    customer: Customer,
    amount: Decimal,
    is_vend_by_unit: bool,
    payment: PaymentNotification,
    idempotency_key: str,
) -> Tuple[bool, Optional[Token], Optional[str]]:
    """
    Core vending flow used by:
    - M-Pesa webhook
    - Payment retry

    Steps:
    - Ensure VendingRequest exists (idempotent on idempotency_key)
    - If already SUCCESS and token linked => return existing token
    - Call Stronpower VendingMeter
    - Create Token (including units, if provided)
    - Update VendingRequest
    """
    # 1. Check for existing request (idempotent)
    vr = VendingRequest.objects.filter(idempotency_key=idempotency_key).select_related(
        "token"
    ).first()

    if vr and vr.status == VendingRequest.SUCCESS and vr.token:
        # Already successfully vended before
        return True, vr.token, None

    # We will create / update inside a transaction
    with transaction.atomic():
        if not vr:
            vr = VendingRequest.objects.create(
                idempotency_key=idempotency_key,
                payment=payment,
                status=VendingRequest.PENDING,
                attempt_count=0,
                request_payload={
                    "meter_id": meter.meter_id,
                    "customer_id": customer.customer_id,
                    "amount": str(amount),
                    "is_vend_by_unit": is_vend_by_unit,
                },
            )

        # 2. Prepare Stronpower credentials
        client = meter.client
        credentials = {
            "company_name": client.stronpower_company_name,
            "username": client.stronpower_username,
            "password": client.stronpower_password,
        }

        stronpower = StronpowerService()
        vr.attempt_count += 1
        vr.sent_at = timezone.now()
        vr.status = VendingRequest.PENDING
        vr.save(update_fields=["attempt_count", "sent_at", "status"])

        # 3. Call Stronpower Vending
        # Now vending_meter returns the FULL JSON payload (list/dict),
        # not just the token string.
        ok, vend_payload, error = stronpower.vending_meter(
            client_credentials=credentials,
            meter_id=meter.meter_id,
            amount=amount,
            is_vend_by_unit=is_vend_by_unit,
            customer_id=customer.customer_id,
        )

        token_value: Optional[str] = None
        units: Optional[Decimal] = None

        if ok and vend_payload:
            # Stronpower usually returns a one-element list with a dict
            # [{
            #   "Token": "...",
            #   "Total_unit": "0.1",
            #   "Unit": "m³",
            #   ...
            # }]
            payload_obj: Any = vend_payload
            if isinstance(payload_obj, list) and payload_obj:
                payload_obj = payload_obj[0]

            if isinstance(payload_obj, dict):
                token_value = (
                    payload_obj.get("Token")
                    or payload_obj.get("token")
                    or payload_obj.get("TokenNo")
                    or payload_obj.get("TokenNo1")
                )

                raw_units = (
                    payload_obj.get("Total_unit")
                    or payload_obj.get("total_unit")
                    or payload_obj.get("Units")
                    or payload_obj.get("units")
                )
                if raw_units is not None:
                    try:
                        units = Decimal(str(raw_units))
                    except (InvalidOperation, TypeError):
                        units = None  # fail silently; amount still stored
            else:
                # Fallback: treat the whole payload as the token string
                token_value = str(payload_obj)

        if not ok or not token_value:
            vr.status = VendingRequest.FAILED
            vr.error_message = error or "Vending failed"
            vr.received_at = timezone.now()
            vr.response_payload = {
                "error": error or "Unknown error",
                "raw_payload": vend_payload,
            }
            vr.save(
                update_fields=[
                    "status",
                    "error_message",
                    "received_at",
                    "response_payload",
                ]
            )
            return False, None, error or "Vending failed"

        # 4. Create token row if missing
        token = vr.token
        if not token:
            token = Token.objects.create(
                token_value=str(token_value),
                token_type=Token.VENDING,
                meter=meter,
                customer=customer,
                payment=payment,
                amount=amount,
                units=units,
                is_vend_by_unit=is_vend_by_unit,
                status=Token.CREATED,
                issued_by=None,
            )
            vr.token = token

        # 5. Update VendingRequest as success
        vr.status = VendingRequest.SUCCESS
        vr.received_at = timezone.now()
        vr.response_payload = {
            "token_value": str(token_value),
            "units": str(units) if units is not None else None,
            "raw_payload": vend_payload,
        }
        vr.error_message = ""
        vr.save(
            update_fields=[
                "status",
                "received_at",
                "response_payload",
                "error_message",
                "token",
            ]
        )

        # 6. Send SMS
        sms_ok = _send_token_sms(token)
        if sms_ok and token.status != Token.DELIVERED:
            token.status = Token.DELIVERED
            token.delivered_at = timezone.now()
            token.save(update_fields=["status", "delivered_at"])

        return True, token, None


def _send_token_sms(token: Token) -> bool:
    """
    Send the 'token issued' SMS for a given token.
    Safe to call even if some fields are missing.
    """
    if not token:
        return False

    customer = token.customer
    meter = token.meter

    if not customer or not customer.phone:
        return False

    if not meter or not meter.meter_id:
        return False

    sms = SMSService()

    context = {
        "meter_id": meter.meter_id,
        "token": token.token_value,
        # If amount is None (e.g. vend by units), fall back to 0
        "amount": token.amount if token.amount is not None else 0,
    }
    return sms.send_template(
        to_number=customer.phone,
        template_name="token_issued",
        context=context,
    )
