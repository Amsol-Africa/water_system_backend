# ============================================
# FILE 6: tokens/serializers.py
# ============================================
from decimal import Decimal
from rest_framework import serializers
from .models import Token, VendingRequest


class TokenSerializer(serializers.ModelSerializer):
    """Serializer for Token model"""

    meter_id = serializers.CharField(source='meter.meter_id', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)

    issued_by_name = serializers.CharField(
        source='issued_by.get_full_name',
        read_only=True
    )
    issued_by_email = serializers.EmailField(
        source='issued_by.email',
        read_only=True
    )
    issued_by_role = serializers.CharField(
        source='issued_by.role',
        read_only=True
    )

    # For linking to the payment screen by M-Pesa Tx
    payment_transaction_id = serializers.CharField(
        source='payment.mpesa_transaction_id',
        read_only=True
    )

    class Meta:
        model = Token
        fields = [
            'id',
            'token_value',
            'token_type',
            'meter',
            'meter_id',
            'customer',
            'customer_name',
            'customer_phone',
            'payment',
            'payment_transaction_id',
            'amount',
            'units',
            'is_vend_by_unit',
            'status',
            'issued_by',
            'issued_by_name',
            'issued_by_email',
            'issued_by_role',
            'created_at',
            'delivered_at',
            'expires_at',
        ]
        read_only_fields = ['id', 'created_at', 'delivered_at']



class IssueTokenSerializer(serializers.Serializer):
    """Serializer for issuing a token"""
    
    meter_id = serializers.UUIDField(required=True)
    customer_id = serializers.UUIDField(required=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True, min_value=Decimal('0.01'))
    is_vend_by_unit = serializers.BooleanField(default=False)
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value


class ClearCreditSerializer(serializers.Serializer):
    """Serializer for clearing credit"""
    
    meter_id = serializers.UUIDField(required=True)
    customer_id = serializers.UUIDField(required=True)


class ClearTamperSerializer(serializers.Serializer):
    """Serializer for clearing tamper"""
    
    meter_id = serializers.UUIDField(required=True)
    customer_id = serializers.UUIDField(required=True)


class VendingRequestSerializer(serializers.ModelSerializer):
    """Serializer for VendingRequest model"""
    
    payment_transaction_id = serializers.CharField(
        source='payment.mpesa_transaction_id', 
        read_only=True
    )
    token_value = serializers.CharField(source='token.token_value', read_only=True)
    
    class Meta:
        model = VendingRequest
        fields = [
            'id', 'idempotency_key', 'token', 'token_value',
            'payment', 'payment_transaction_id', 'request_payload',
            'response_payload', 'status', 'attempt_count',
            'error_message', 'sent_at', 'received_at', 'next_retry_at',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']