# ============================================
# FILE: integrations/sms_service.py
# ============================================
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


class SmsService:
    """
    Very simple SMS sender abstraction.

    For now it just logs the SMS. Later you can plug in
    Twilio, Africa's Talking, etc.
    """

    def __init__(self) -> None:
        # place to add API keys, base URLs, etc.
        pass

    def send_sms(self, phone: str, message: str) -> None:
        """
        Simulate sending an SMS by logging it.
        """
        safe_phone = phone or "<no-phone>"
        logger.info(f"[SMS] To {safe_phone}: {message}")
