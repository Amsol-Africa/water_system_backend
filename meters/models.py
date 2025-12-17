# ============================================
# FILE 4: meters/models.py - Meter Models
# ============================================
from django.db import models
from django.core.validators import MinValueValidator
import uuid
from customers.models import Customer


class Meter(models.Model):
    """Water meter management"""
    
    ACTIVE = 'active'
    SUSPENDED = 'suspended'
    TAMPER = 'tamper'
    FAULT = 'fault'
    OFFLINE = 'offline'
    MAINTENANCE = 'maintenance'
    
    STATUS_CHOICES = [
        (ACTIVE, 'Active'),
        (SUSPENDED, 'Suspended'),
        (TAMPER, 'Tamper'),
        (FAULT, 'Fault'),
        (OFFLINE, 'Offline'),
        (MAINTENANCE, 'Maintenance'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meter_id = models.CharField(max_length=50, unique=True, db_index=True)
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='meters')
    meter_type = models.CharField(max_length=100)
    location = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=ACTIVE)
    firmware_version = models.CharField(max_length=50, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)
    installed_on = models.DateField(null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    last_tamper_event = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'meters'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client', 'status']),
            models.Index(fields=['meter_id']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.meter_id} - {self.status}"


class MeterAssignment(models.Model):
    """Links customers to meters"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meter = models.ForeignKey(Meter, on_delete=models.CASCADE, related_name='assignments')
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, related_name='meter_assignments')
    assigned_on = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    deactivated_on = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'meter_assignments'
        ordering = ['-assigned_on']
        indexes = [
            models.Index(fields=['meter', 'is_active']),
            models.Index(fields=['customer', 'is_active']),
        ]
        unique_together = [['meter', 'customer', 'is_active']]
    
    def __str__(self):
        return f"{self.customer.name} -> {self.meter.meter_id}"