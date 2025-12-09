# ============================================
# FILE 10: core/dashboard_views.py (UPDATED)
# ============================================
from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from meters.models import Meter
from customers.models import Customer
from tokens.models import Token
from payments.models import PaymentNotification


def _get_scoped_querysets(user):
  """
  Scope all dashboard data to the current user.
  System admin -> all data.
  Client user   -> client-only data.
  """
  if getattr(user, "is_system_admin", False):
    meter_qs = Meter.objects.all()
    customer_qs = Customer.objects.all()
    token_qs = Token.objects.all()
    payment_qs = PaymentNotification.objects.all()
  else:
    client_id = getattr(user, "client_id", None)
    meter_qs = Meter.objects.filter(client_id=client_id)
    customer_qs = Customer.objects.filter(client_id=client_id)
    token_qs = Token.objects.filter(meter__client_id=client_id)
    payment_qs = PaymentNotification.objects.filter(client_id=client_id)

  return meter_qs, customer_qs, token_qs, payment_qs


class DashboardStatsView(APIView):
  """Dashboard statistics"""
  permission_classes = [IsAuthenticated]

  def get(self, request):
    user = request.user
    meter_qs, customer_qs, token_qs, payment_qs = _get_scoped_querysets(user)

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)

    # Meters
    total_meters = meter_qs.count()
    active_meters = meter_qs.filter(status="active").count()
    fault_meters = meter_qs.filter(status="fault").count()
    tamper_meters = meter_qs.filter(status="tamper").count()
    offline_meters = meter_qs.filter(status="offline").count()

    # Customers
    total_customers = customer_qs.count()

    # Tokens
    tokens_issued = token_qs.count()
    tokens_issued_today = token_qs.filter(created_at__gte=today_start).count()
    tokens_issued_7d = token_qs.filter(created_at__gte=week_start).count()
    tokens_issued_30d = token_qs.filter(created_at__gte=month_start).count()

    # Payments / revenue
    verified_payments = payment_qs.filter(status=PaymentNotification.VERIFIED)

    def _sum_amount(qs, **extra_filters):
      return (
        qs.filter(**extra_filters).aggregate(total=Sum("amount"))["total"]
        or 0
      )

    total_revenue = _sum_amount(verified_payments)
    revenue_today = _sum_amount(verified_payments, received_at__gte=today_start)
    revenue_7d = _sum_amount(verified_payments, received_at__gte=week_start)
    revenue_30d = _sum_amount(verified_payments, received_at__gte=month_start)

    pending_payments = payment_qs.filter(
      status=PaymentNotification.PENDING
    ).count()
    failed_payments = payment_qs.filter(
      status=PaymentNotification.FAILED
    ).count()

    stats = {
      "total_meters": total_meters,
      "active_meters": active_meters,
      "fault_meters": fault_meters,
      "tamper_meters": tamper_meters,
      "offline_meters": offline_meters,
      "total_customers": total_customers,
      "tokens_issued": tokens_issued,
      "tokens_issued_today": tokens_issued_today,
      "tokens_issued_7d": tokens_issued_7d,
      "tokens_issued_30d": tokens_issued_30d,
      "total_revenue": total_revenue,
      "revenue_today": revenue_today,
      "revenue_7d": revenue_7d,
      "revenue_30d": revenue_30d,
      "pending_payments": pending_payments,
      "failed_payments": failed_payments,
    }

    return Response(stats)


class RecentActivityView(APIView):
  """Recent activity feed (payments + tokens)"""
  permission_classes = [IsAuthenticated]

  def get(self, request):
    user = request.user
    _, _, token_qs, payment_qs = _get_scoped_querysets(user)

    # Latest 10 payments & 10 tokens
    payments = list(
      payment_qs.select_related("customer")
      .order_by("-received_at")[:10]
    )
    tokens = list(
      token_qs.select_related("meter", "customer")
      .order_by("-created_at")[:10]
    )

    activities = []

    # Map payments
    for p in payments:
      activities.append({
        "type": "payment",
        "id": str(p.id),
        "timestamp": p.received_at,
        "status": p.status,
        "title": f"Payment KES {p.amount} from {p.phone}",
        "subtitle": f"Meter {p.account_number or '-'} · Tx {p.mpesa_transaction_id}",
        "customer_name": getattr(p.customer, "name", None),
        "meter_id": p.account_number,
        "amount": p.amount,
        "links": {
          "payment": str(p.id),
          "tokens_for_payment": str(p.id),
        },
      })

    # Map tokens
    for t in tokens:
      activities.append({
        "type": "token",
        "id": str(t.id),
        "timestamp": t.created_at,
        "status": t.status,
        "title": f"Token issued for meter {t.meter.meter_id if t.meter else '-'}",
        "subtitle": f"{t.amount or 0} KES · {getattr(t.customer, 'name', '-')}",
        "customer_name": getattr(t.customer, "name", None),
        "meter_id": t.meter.meter_id if t.meter else None,
        "amount": t.amount,
        "links": {
          "token": str(t.id),
          "payment": str(getattr(t.payment, "id", "")) if t.payment else None,
        },
      })

    # Sort by timestamp desc & limit
    activities = sorted(
      activities,
      key=lambda x: x["timestamp"] or timezone.now(),
      reverse=True,
    )[:20]

    # Make timestamps JSON-friendly
    for a in activities:
      if a["timestamp"]:
        a["timestamp"] = a["timestamp"].isoformat()

    return Response(activities)


class ChartsDataView(APIView):
  """Charts data for dashboard"""
  permission_classes = [IsAuthenticated]

  def get(self, request):
    user = request.user
    meter_qs, _, token_qs, payment_qs = _get_scoped_querysets(user)

    period = request.query_params.get("period", "week")
    now = timezone.now()

    days = {
      "week": 7,
      "month": 30,
      "quarter": 90,
      "year": 365,
    }.get(period, 7)

    start_date = now - timedelta(days=days)

    # Tokens over time
    tokens_qs = (
      token_qs.filter(created_at__gte=start_date)
      .annotate(date=TruncDate("created_at"))
      .values("date")
      .annotate(
        tokens=Count("id"),
        amount=Sum("amount"),
      )
      .order_by("date")
    )
    tokens_over_time = [
      {
        "date": row["date"].isoformat(),
        "tokens": row["tokens"],
        "amount": row["amount"] or 0,
      }
      for row in tokens_qs
    ]

    # Revenue over time (verified payments)
    revenue_qs = (
      payment_qs.filter(
        status=PaymentNotification.VERIFIED,
        received_at__gte=start_date,
      )
      .annotate(date=TruncDate("received_at"))
      .values("date")
      .annotate(revenue=Sum("amount"))
      .order_by("date")
    )
    revenue_over_time = [
      {
        "date": row["date"].isoformat(),
        "revenue": row["revenue"] or 0,
      }
      for row in revenue_qs
    ]

    # Meter status distribution
    status_qs = (
      meter_qs.values("status")
      .annotate(count=Count("id"))
      .order_by("status")
    )
    meter_status_distribution = [
      {
        "status": row["status"] or "unknown",
        "count": row["count"],
      }
      for row in status_qs
    ]

    charts = {
      "tokens_over_time": tokens_over_time,
      "revenue_over_time": revenue_over_time,
      "meter_status_distribution": meter_status_distribution,
    }

    return Response(charts)
