# ============================================
# FILE 7: tokens/models.py - Token Models
# ============================================
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid


class Token(models.Model):
    """Vending tokens"""
    
    CREATED = 'created'
    DELIVERED = 'delivered'
    REDEEMED = 'redeemed'
    EXPIRED = 'expired'
    FAILED = 'failed'
    
    STATUS_CHOICES = [
        (CREATED, 'Created'),
        (DELIVERED, 'Delivered'),
        (REDEEMED, 'Redeemed'),
        (EXPIRED, 'Expired'),
        (FAILED, 'Failed'),
    ]
    
    VENDING = 'vending'
    CLEAR_CREDIT = 'clear_credit'
    CLEAR_TAMPER = 'clear_tamper'
    
    TOKEN_TYPE_CHOICES = [
        (VENDING, 'Vending Token'),
        (CLEAR_CREDIT, 'Clear Credit Token'),
        (CLEAR_TAMPER, 'Clear Tamper Token'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token_value = models.CharField(max_length=255)
    token_type = models.CharField(max_length=20, choices=TOKEN_TYPE_CHOICES, default=VENDING)
    meter = models.ForeignKey('meters.Meter', on_delete=models.CASCADE, related_name='tokens')
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, related_name='tokens')
    payment = models.ForeignKey('payments.PaymentNotification', on_delete=models.SET_NULL, null=True, blank=True, related_name='tokens')
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.01'))])
    units = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_vend_by_unit = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=CREATED)
    issued_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='issued_tokens')
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'tokens'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['meter', 'status']),
            models.Index(fields=['customer', 'created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.token_type} - {self.meter.meter_id} - {self.status}"


class VendingRequest(models.Model):
    """Tracks API requests to Stronpower"""
    
    PENDING = 'pending'
    SUCCESS = 'success'
    FAILED = 'failed'
    RETRYING = 'retrying'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (SUCCESS, 'Success'),
        (FAILED, 'Failed'),
        (RETRYING, 'Retrying'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    idempotency_key = models.CharField(max_length=100, unique=True, db_index=True)
    token = models.OneToOneField(Token, on_delete=models.CASCADE, related_name='vending_request', null=True, blank=True)
    payment = models.ForeignKey('payments.PaymentNotification', on_delete=models.CASCADE, related_name='vending_requests')
    request_payload = models.JSONField(default=dict)
    response_payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    attempt_count = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'vending_requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'next_retry_at']),
            models.Index(fields=['idempotency_key']),
            models.Index(fields=['payment']),
        ]
    
    def __str__(self):
        return f"Request {self.idempotency_key} - {self.status}"