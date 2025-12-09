# ============================================
# FILE 10: core/health_urls.py
# ============================================
from django.urls import path
from . import health_views

app_name = 'health'

urlpatterns = [
    path('', health_views.HealthCheckView.as_view(), name='health'),
    path('ready/', health_views.ReadinessCheckView.as_view(), name='ready'),
]
