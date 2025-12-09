# core/schema_serializers.py
from decimal import Decimal
from rest_framework import serializers
from accounts.serializers import UserSerializer  # reuse your existing serializer

class MessageSerializer(serializers.Serializer):
    message = serializers.CharField()
    error = serializers.CharField(required=False)

# Auth
class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()

class LogoutRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False)

# Alerts
class AckRequestSerializer(serializers.Serializer):
    # If your ack endpoint has no body, you can leave this empty or set request=None in @extend_schema
    pass

# Customers
class AssignMeterRequestSerializer(serializers.Serializer):
    meter_id = serializers.UUIDField()

class UnassignMeterRequestSerializer(serializers.Serializer):
    meter_id = serializers.UUIDField()

# Meters
class MeterQueryRequestSerializer(serializers.Serializer):
    meter_id = serializers.CharField()  # adjust to UUIDField if that’s your type

# Payments / Tokens (stubs if you need them later)
class PaymentRetryRequestSerializer(serializers.Serializer):
    payment_id = serializers.UUIDField()

class PaymentReconcileRequestSerializer(serializers.Serializer):
    from_date = serializers.DateField()
    to_date = serializers.DateField()

class IssueTokenRequestSerializer(serializers.Serializer):
    meter_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.00"))
    
# Dashboard
class DashboardStatsSerializer(serializers.Serializer):
    total_customers = serializers.IntegerField()
    active_meters = serializers.IntegerField()
    daily_volume_litres = serializers.IntegerField()
    revenue_today = serializers.DecimalField(max_digits=12, decimal_places=2)

class ActivityItemSerializer(serializers.Serializer):
    type = serializers.CharField()
    message = serializers.CharField()
    created_at = serializers.DateTimeField()

class ChartPointSerializer(serializers.Serializer):
    x = serializers.CharField()
    y = serializers.FloatField()

class ChartsResponseSerializer(serializers.Serializer):
    sales = ChartPointSerializer(many=True)
    volume = ChartPointSerializer(many=True)

# Payments
class PaymentRetryRequestSerializer(serializers.Serializer):
    payment_id = serializers.UUIDField()

class PaymentReconcileRequestSerializer(serializers.Serializer):
    from_date = serializers.DateField()
    to_date = serializers.DateField()

# Reports (shape depends on your endpoints; keep generic rows)
class ReportRowSerializer(serializers.Serializer):
    columns = serializers.DictField(child=serializers.JSONField())

class MeterUsageReportResponse(serializers.Serializer):
    rows = ReportRowSerializer(many=True)

class TamperEventsReportResponse(serializers.Serializer):
    rows = ReportRowSerializer(many=True)

class TokensReportResponse(serializers.Serializer):
    rows = ReportRowSerializer(many=True)

class TransactionsReportResponse(serializers.Serializer):
    rows = ReportRowSerializer(many=True)

# Tokens
class ClearFlagRequestSerializer(serializers.Serializer):
    meter_id = serializers.UUIDField()

class IssueTokenRequestSerializer(serializers.Serializer):
    meter_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.00"))

# Webhooks
class MPesaWebhookSerializer(serializers.Serializer):
    # Put the actual fields your webhook receives; placeholders below:
    Body = serializers.DictField()

class MPesaCallbackSerializer(serializers.Serializer):
    Body = serializers.DictField()

# Health
class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()
