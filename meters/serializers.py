# meters/serializers.py
from rest_framework import serializers
from django.db.models import Sum, Max
from decimal import Decimal

from .models import Meter, MeterAssignment
from tokens.models import Token 


class MeterSerializer(serializers.ModelSerializer):
    """Serializer for Meter model"""
    
    client_name = serializers.CharField(source='client.name', read_only=True)
    assignments_count = serializers.IntegerField(
        source='assignments.filter(is_active=True).count', 
        read_only=True
    )


    total_paid = serializers.SerializerMethodField()
    total_units = serializers.SerializerMethodField()
    total_vends = serializers.SerializerMethodField()
    last_vended_at = serializers.SerializerMethodField()
    last_token_value = serializers.SerializerMethodField()
    last_customer_name = serializers.SerializerMethodField()
    last_customer_id = serializers.SerializerMethodField()
    current_customer_name = serializers.SerializerMethodField()
    current_customer_id = serializers.SerializerMethodField()
    
    class Meta:
        model = Meter
        fields = [
            'id', 'meter_id', 'client', 'client_name', 'meter_type', 
            'location', 'status', 'firmware_version', 'serial_number',
            'installed_on', 'last_seen', 'last_tamper_event', 
            'metadata', 'assignments_count',
            'total_paid', 'total_units', 'total_vends',
            'last_vended_at', 'last_token_value', 'last_customer_name',
            'last_customer_id', 'current_customer_name', 'current_customer_id',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_meter_id(self, value):
        """Ensure meter_id is unique"""
        if self.instance:
            # Update case
            if Meter.objects.exclude(pk=self.instance.pk).filter(meter_id=value).exists():
                raise serializers.ValidationError("Meter with this ID already exists")
        else:
            # Create case
            if Meter.objects.filter(meter_id=value).exists():
                raise serializers.ValidationError("Meter with this ID already exists")
        return value

    # ---------- System totals helpers (from our DB) ----------

    def _vending_qs(self, obj):
        """
        All successful vending tokens for this meter in *our* system.
        Excludes failed tokens, only VENDING type.
        """
        return (
            Token.objects
            .filter(meter=obj, token_type=Token.VENDING)
            .exclude(status=Token.FAILED)
        )

    def get_total_paid(self, obj):
        agg = self._vending_qs(obj).aggregate(total=Sum('amount'))
        return agg['total'] or Decimal('0.00')

    def get_total_units(self, obj):
        agg = self._vending_qs(obj).aggregate(total=Sum('units'))
        return agg['total'] or Decimal('0.00')

    def get_total_vends(self, obj):
        return self._vending_qs(obj).count()

    def get_last_vended_at(self, obj):
        agg = self._vending_qs(obj).aggregate(last=Max('created_at'))
        return agg['last']

    def get_last_token_value(self, obj):
        last = self._vending_qs(obj).order_by('-created_at').first()
        return last.token_value if last else None

    def get_last_customer_name(self, obj):
        last = (
            self._vending_qs(obj)
            .select_related('customer')
            .order_by('-created_at')
            .first()
        )
        if last and last.customer:
            return last.customer.name
        return None
       
    def get_last_customer_id(self, obj):
        last = (
            self._vending_qs(obj)
            .select_related('customer')
            .order_by('-created_at')
            .first()
        )
        if last and last.customer:
            return str(last.customer.id)
        return None
    
    def get_current_customer_name(self, obj):
        assignment = (
            obj.assignments
            .filter(is_active=True)
            .select_related('customer')
            .order_by('-assigned_on')
            .first()
        )
        if assignment and assignment.customer:
            return assignment.customer.name
        return None

    def get_current_customer_id(self, obj):
        assignment = (
            obj.assignments
            .filter(is_active=True)
            .select_related('customer')
            .order_by('-assigned_on')
            .first()
        )
        if assignment and assignment.customer:
            return str(assignment.customer.id)
        return None
    
    def _active_assignment(self, obj):
        return (
            obj.assignments
            .filter(is_active=True)
            .select_related('customer')
            .order_by('-assigned_on')
        ).first()

class MeterAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for MeterAssignment model"""
    
    meter_id = serializers.CharField(source='meter.meter_id', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_id = serializers.CharField(source='customer.customer_id', read_only=True)
    
    class Meta:
        model = MeterAssignment
        fields = [
            'id', 'meter', 'meter_id', 'customer', 'customer_name', 
            'customer_id', 'assigned_on', 'is_active', 'deactivated_on'
        ]
        read_only_fields = ['id', 'assigned_on', 'deactivated_on']


class MeterQuerySerializer(serializers.Serializer):
    """Serializer for querying meter info from Stronpower"""
    
    meter_id = serializers.CharField(required=True)