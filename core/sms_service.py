# ============================================
# FILE: core/sms_service.py
# ============================================
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

try:
    from twilio.rest import Client as TwilioClient
except ImportError:  # Twilio optional
    TwilioClient = None

try:
    import africastalking
except ImportError:  # Africa's Talking optional
    africastalking = None


class SMSService:
    """
    SMS abstraction that can use:
    - Twilio  (SMS_PROVIDER = 'twilio')
    - Africa's Talking (SMS_PROVIDER = 'africastalking')
    - fallback: just logs
    """

    def __init__(self):
        self.provider = getattr(settings, "SMS_PROVIDER", "").lower()

        self.twilio_client = None
        self.twilio_from = None

        self.at_initialized = False
        self.at_sms = None
        self.at_sender_id = None

        if self.provider == "twilio":
            if not TwilioClient:
                logger.warning("Twilio client not installed but SMS_PROVIDER=twilio")
            else:
                self.twilio_client = TwilioClient(
                    getattr(settings, "TWILIO_ACCOUNT_SID", ""),
                    getattr(settings, "TWILIO_AUTH_TOKEN", ""),
                )
                self.twilio_from = getattr(settings, "TWILIO_PHONE_NUMBER", "")
                if not self.twilio_from:
                    logger.warning("TWILIO_PHONE_NUMBER not configured")

        elif self.provider == "africastalking":
            if not africastalking:
                logger.warning(
                    "africastalking package not installed but SMS_PROVIDER=africastalking"
                )
            else:
                username = getattr(settings, "AFRICASTALKING_USERNAME", "")
                api_key = getattr(settings, "AFRICASTALKING_API_KEY", "")
                if not username or not api_key:
                    logger.warning("Africa's Talking credentials not configured")
                else:
                    africastalking.initialize(username, api_key)
                    self.at_sms = africastalking.SMS
                    self.at_sender_id = getattr(settings, "AFRICASTALKING_SENDER_ID", "")
                    self.at_initialized = True

    def send(self, to_number: str, message: str) -> bool:
        """
        Send SMS. Returns True if *we think* it was accepted by provider,
        False otherwise.
        """
        to_number = str(to_number).strip()
        if not to_number:
            logger.error("SMS send failed: missing destination phone")
            return False

        # Twilio
        if self.provider == "twilio" and self.twilio_client and self.twilio_from:
            try:
                msg = self.twilio_client.messages.create(
                    body=message,
                    from_=self.twilio_from,
                    to=to_number,
                )
                logger.info(
                    "SMS sent via Twilio",
                    extra={"to": to_number, "sid": msg.sid},
                )
                return True
            except Exception as e:
                logger.error(
                    f"Twilio SMS sending failed: {e}",
                    extra={"to": to_number},
                )
                return False

        # Africa's Talking
        if self.provider == "africastalking" and self.at_initialized and self.at_sms:
            try:
                response = self.at_sms.send(
                    message,
                    [to_number],
                    sender_id=self.at_sender_id or None,
                )
                logger.info(
                    "SMS sent via Africa's Talking",
                    extra={"to": to_number, "response": response},
                )
                return True
            except Exception as e:
                logger.error(
                    f"Africa's Talking SMS sending failed: {e}",
                    extra={"to": to_number},
                )
                return False

        # Fallback: just log
        logger.info(f"[SMS-FAKE] To {to_number}: {message}")
        return True

    def send_template(self, to_number: str, template_name: str, context: dict) -> bool:
        """Send SMS using a small template library"""

        templates = {
            "token_issued": (
                "Your water token for meter {meter_id} is: {token}. "
                "Amount: KES {amount}"
            ),
            "low_balance": "Your meter {meter_id} balance is low. Please top up.",
            "tamper_alert": "ALERT: Tamper detected on meter {meter_id}. Contact support.",
        }

        template = templates.get(template_name)
        if not template:
            logger.error(f"Unknown SMS template: {template_name}")
            return False

        try:
            message = template.format(**context)
        except Exception as e:
            logger.error(f"Error formatting SMS template '{template_name}': {e}")
            return False

        return self.send(to_number, message)
