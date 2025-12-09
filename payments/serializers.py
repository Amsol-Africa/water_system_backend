# ============================================
#  payments/serializers.py
# ============================================
from rest_framework import serializers
from .models import PaymentNotification


class PaymentNotificationSerializer(serializers.ModelSerializer):
    """Serializer for PaymentNotification model"""
    
    client_name = serializers.CharField(source='client.name', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    tokens_count = serializers.IntegerField(source='tokens.count', read_only=True)
    
    class Meta:
        model = PaymentNotification
        fields = [
            'id', 'mpesa_transaction_id', 'amount', 'paybill', 
            'account_number', 'phone', 'client', 'client_name',
            'customer', 'customer_name', 'status', 'raw_payload',
            'error_message', 'tokens_count',
            'received_at', 'processed_at'
        ]
        read_only_fields = ['id', 'received_at', 'processed_at']