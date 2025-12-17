# ============================================
# FILE 8: alerts/models.py - Alert Model
# ============================================
from django.db import models
import uuid


class Alert(models.Model):
    """System and meter alerts"""
    
    LOW_TOKEN = 'low_token'
    TAMPER = 'tamper'
    FAULT = 'fault'
    OFFLINE = 'offline'
    PAYMENT_FAILED = 'payment_failed'
    VENDING_FAILED = 'vending_failed'
    
    ALERT_TYPE_CHOICES = [
        (LOW_TOKEN, 'Low Token Warning'),
        (TAMPER, 'Tamper Alert'),
        (FAULT, 'Meter Fault'),
        (OFFLINE, 'Meter Offline'),
        (PAYMENT_FAILED, 'Payment Failed'),
        (VENDING_FAILED, 'Vending Failed'),
    ]
    
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'
    
    SEVERITY_CHOICES = [
        (INFO, 'Info'),
        (WARNING, 'Warning'),
        (ERROR, 'Error'),
        (CRITICAL, 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default=WARNING)
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='alerts')
    meter = models.ForeignKey('meters.Meter', on_delete=models.CASCADE, null=True, blank=True, related_name='alerts')
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, null=True, blank=True, related_name='alerts')
    message = models.TextField()
    sent_to = models.JSONField(default=list)
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='acknowledged_alerts')
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'alerts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client', 'is_acknowledged']),
            models.Index(fields=['alert_type', 'severity']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.alert_type} - {self.severity} - {self.created_at}"