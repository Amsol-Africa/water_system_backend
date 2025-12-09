# ============================================
#  payments/urls.py 
# ============================================
from django.urls import path
from . import views
from .webhook_views import MPesaWebhookView, MPesaCallbackView

app_name = 'payments'

urlpatterns = [
    path('', views.PaymentListView.as_view(), name='payment_list'),
    path('<uuid:pk>/', views.PaymentRetrieveView.as_view(), name='payment_detail'),
    path('<uuid:pk>/retry/', views.PaymentRetryView.as_view(), name='payment_retry'),
    path('reconcile/', views.PaymentReconcileView.as_view(), name='payment_reconcile'),

    # M-Pesa endpoints (public)
    path('webhooks/c2b/', MPesaWebhookView.as_view(), name='c2b_webhook'),
    path('callbacks/c2b/', MPesaCallbackView.as_view(), name='c2b_callback'),
]

