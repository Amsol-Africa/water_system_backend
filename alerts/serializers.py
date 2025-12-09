# ============================================
# FILE 7: alerts/serializers.py
# ============================================
from rest_framework import serializers
from .models import Alert


class AlertSerializer(serializers.ModelSerializer):
    """Serializer for Alert model"""
    
    client_name = serializers.CharField(source='client.name', read_only=True)
    meter_id = serializers.CharField(source='meter.meter_id', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    acknowledged_by_name = serializers.CharField(
        source='acknowledged_by.get_full_name', 
        read_only=True
    )
    
    class Meta:
        model = Alert
        fields = [
            'id', 'alert_type', 'severity', 'client', 'client_name',
            'meter', 'meter_id', 'customer', 'customer_name',
            'message', 'sent_to', 'is_acknowledged',
            'acknowledged_by', 'acknowledged_by_name', 'acknowledged_at',
            'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'acknowledged_at']


class AlertAcknowledgeSerializer(serializers.Serializer):
    """Serializer for acknowledging an alert"""
    
    pass  # No additional fields needed