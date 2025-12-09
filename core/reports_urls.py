# ============================================
# FILE 12: core/reports_urls.py
# ============================================
from django.urls import path
from . import reports_views

app_name = 'reports'

urlpatterns = [
    path('transactions/', reports_views.TransactionsReportView.as_view(), name='transactions'),
    path('meter-usage/', reports_views.MeterUsageReportView.as_view(), name='meter_usage'),
    path('tokens/', reports_views.TokensReportView.as_view(), name='tokens'),
    path('tamper-events/', reports_views.TamperEventsReportView.as_view(), name='tamper_events'),
]