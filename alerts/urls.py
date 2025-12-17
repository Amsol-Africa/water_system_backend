# ============================================
# FILE 9: alerts/urls.py
# ============================================
from django.urls import path
from . import views

app_name = 'alerts'

urlpatterns = [
    path('', views.AlertListView.as_view(), name='alert_list'),
    path('<uuid:pk>/', views.AlertRetrieveView.as_view(), name='alert_detail'),
    path('<uuid:pk>/acknowledge/', views.AlertAcknowledgeView.as_view(), name='alert_acknowledge'),
]
