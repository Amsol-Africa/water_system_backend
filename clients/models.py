# ============================================
#  clients/models.py - Client Model
# ============================================
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField
import uuid

class Client(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    company_info = models.TextField(blank=True)
    paybill_number = models.CharField(max_length=20, unique=True)

    # Encrypted fields (Django 5–friendly)
    stronpower_company_name = EncryptedCharField(max_length=255, blank=True, null=True)
    stronpower_username     = EncryptedCharField(max_length=255, blank=True, null=True)
    stronpower_password     = EncryptedCharField(max_length=255, blank=True, null=True)

    billing_info = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'clients'
        ordering = ['name']
        indexes = [
            models.Index(fields=['paybill_number']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name
