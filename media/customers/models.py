# ============================================
# FILE 5: customers/models.py - Customer Model
# ============================================
from django.db import models
import uuid


class Customer(models.Model):
    """Customer management"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='customers')
    customer_id = models.CharField(max_length=100, db_index=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    id_number = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'customers'
        ordering = ['-created_at']
        unique_together = [['client', 'customer_id']]
        indexes = [
            models.Index(fields=['client', 'phone']),
            models.Index(fields=['customer_id']),
            models.Index(fields=['phone']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.customer_id})"