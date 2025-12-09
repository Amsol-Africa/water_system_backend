# ============================================
# FILE 11: core/dashboard_urls.py
# ============================================
from django.urls import path
from . import dashboard_views

app_name = 'dashboard'

urlpatterns = [
    path('stats/', dashboard_views.DashboardStatsView.as_view(), name='stats'),
    path('recent-activity/', dashboard_views.RecentActivityView.as_view(), name='recent_activity'),
    path('charts/', dashboard_views.ChartsDataView.as_view(), name='charts'),
]