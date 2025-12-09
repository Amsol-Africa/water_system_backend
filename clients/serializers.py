# ============================================
# FILE 2: clients/serializers.py
# ============================================
from rest_framework import serializers
from .models import Client


class ClientSerializer(serializers.ModelSerializer):
    """Serializer for Client model"""
    
    # Count related objects
    meters_count = serializers.IntegerField(source='meters.count', read_only=True)
    customers_count = serializers.IntegerField(source='customers.count', read_only=True)
    users_count = serializers.IntegerField(source='users.count', read_only=True)
    
    class Meta:
        model = Client
        fields = [
            'id', 'name', 'company_info', 'paybill_number',
            'stronpower_company_name', 'stronpower_username', 'stronpower_password',
            'billing_info', 'is_active', 
            'meters_count', 'customers_count', 'users_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'stronpower_password': {'write_only': True}
        }


class ClientStatsSerializer(serializers.Serializer):
    """Serializer for client statistics"""
    
    total_meters = serializers.IntegerField()
    active_meters = serializers.IntegerField()
    total_customers = serializers.IntegerField()
    total_tokens = serializers.IntegerField()
    total_payments = serializers.DecimalField(max_digits=15, decimal_places=2)
    recent_alerts = serializers.IntegerField()