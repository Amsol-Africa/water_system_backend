# ============================================
# customers/serializers.py
# ============================================
from rest_framework import serializers
from django.db.models import Sum, Count, Max
from decimal import Decimal
from .models import Customer
from meters.models import MeterAssignment
from tokens.models import Token


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer for Customer model"""

    client_name = serializers.CharField(source='client.name', read_only=True)
    meters_count = serializers.SerializerMethodField()  

    # System stats
    total_tokens = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    total_units = serializers.SerializerMethodField()
    last_vended_at = serializers.SerializerMethodField()

    # Active meters summary for UI
    active_meters = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            'id',
            'client',
            'client_name',
            'customer_id',
            'name',
            'phone',
            'email',
            'address',
            'id_number',
            'is_active',
            'metadata',
            'meters_count',
            'total_tokens',
            'total_paid',
            'total_units',
            'last_vended_at',
            'active_meters',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'client',
            'client_name',
            'customer_id',
            'created_at',
            'updated_at',
        ]
        extra_kwargs = {
            'client': {'required': False},
            'customer_id': {'required': False},
        }

    # --- stats helpers ---

    def _vending_qs(self, obj):
        return Token.objects.filter(
            customer=obj,
            token_type=Token.VENDING,
        ).exclude(status=Token.FAILED)

    def get_total_tokens(self, obj):
        return self._vending_qs(obj).count()

    def get_total_paid(self, obj):
        agg = self._vending_qs(obj).aggregate(total=Sum('amount'))
        return agg['total'] or Decimal('0.00')

    def get_total_units(self, obj):
        agg = self._vending_qs(obj).aggregate(total=Sum('units'))
        return agg['total'] or Decimal('0.00')

    def get_last_vended_at(self, obj):
        agg = self._vending_qs(obj).aggregate(last=Max('created_at'))
        return agg['last']
    
    def get_meters_count(self, obj):
        return obj.meter_assignments.filter(is_active=True).count()


    def get_active_meters(self, obj):
        qs = obj.meter_assignments.filter(is_active=True).select_related('meter')
        result = []
        for ma in qs:
            m = ma.meter
            result.append({
                "assignment_id": ma.id,
                "meter_uuid": str(m.id),
                "meter_id": m.meter_id,
                "location": m.location,
                "status": m.status,
                "assigned_on": ma.assigned_on,
            })
        return result

    def validate(self, attrs):
        """
        Only do uniqueness check if both client & customer_id are known.
        (client will be injected in the view's perform_create)
        """
        client = attrs.get('client') or getattr(getattr(self.context.get('request'), 'user', None), 'client', None)
        customer_id = attrs.get('customer_id')

        if client and customer_id:
            qs = Customer.objects.filter(client=client, customer_id=customer_id)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({
                    'customer_id': 'Customer with this ID already exists for this client'
                })

        return attrs


    def create(self, validated_data):
        """
        Auto-generate customer_id if not provided: e.g. DIC-00001
        """
        if not validated_data.get('customer_id'):
            client = validated_data['client']
            prefix = (client.name or 'CUST')[:3].upper()
            last = (
                Customer.objects
                .filter(client=client, customer_id__startswith=f"{prefix}-")
                .order_by('-created_at')
                .first()
            )
            next_num = 1
            if last and last.customer_id and '-' in last.customer_id:
                try:
                    last_num = int(last.customer_id.split('-')[-1])
                    next_num = last_num + 1
                except ValueError:
                    pass
            validated_data['customer_id'] = f"{prefix}-{next_num:05d}"

        return super().create(validated_data)


class CustomerAssignMeterSerializer(serializers.Serializer):
    """Serializer for assigning/unassigning a meter to a customer."""

    # Accept either meter PK (UUID) or meter.meter_id string
    meter_id = serializers.CharField(required=True)

    def validate_meter_id(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Meter ID is required.")
        return value