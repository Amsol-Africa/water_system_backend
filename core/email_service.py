# ============================================
# FILE 6: core/email_service.py - Email Service
# ============================================
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails"""
    
    def send(self, to_email, subject, message, html_message=None):
        """Send email"""
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                html_message=html_message,
                fail_silently=False
            )
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
        
        except Exception as e:
            logger.error(f"Email sending failed: {str(e)}")
            return False
    
    def send_template(self, to_email, template_name, context):
        """Send email using HTML template"""
        
        try:
            subject_templates = {
                'token_issued': 'Token Issued Successfully',
                'alert_notification': 'Alert Notification',
                'payment_confirmation': 'Payment Confirmation',
            }
            
            subject = subject_templates.get(template_name, 'Amsol Notification')
            
            html_message = render_to_string(
                f'emails/{template_name}.html',
                context
            )
            
            plain_message = render_to_string(
                f'emails/{template_name}.txt',
                context
            ) if f'emails/{template_name}.txt' else None
            
            return self.send(to_email, subject, plain_message or '', html_message)
        
        except Exception as e:
            logger.error(f"Template email failed: {str(e)}")
            return False
