# ============================================
#  payments/models.py - Payment Model
# ============================================
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid


class PaymentNotification(models.Model):
    """M-Pesa payment webhook notifications"""
    
    PENDING = 'pending'
    VERIFIED = 'verified'
    FAILED = 'failed'
    REFUNDED = 'refunded'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (VERIFIED, 'Verified'),
        (FAILED, 'Failed'),
        (REFUNDED, 'Refunded'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mpesa_transaction_id = models.CharField(max_length=100, unique=True, db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    paybill = models.CharField(max_length=20)
    account_number = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='payments', null=True)
    customer = models.ForeignKey('customers.Customer', on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    raw_payload = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'payment_notifications'
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['client', 'status']),
            models.Index(fields=['mpesa_transaction_id']),
            models.Index(fields=['status', 'received_at']),
        ]
    
    def __str__(self):
        return f"{self.mpesa_transaction_id} - {self.amount} - {self.status}"
