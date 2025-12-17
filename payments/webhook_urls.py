# ============================================
#  payments/webhook_urls.py
# ============================================
from django.urls import path
from . import webhook_views

app_name = 'webhooks'

urlpatterns = [
    path('', webhook_views.MPesaWebhookView.as_view(), name='c2b_webhook'),
    path('callback/', webhook_views.MPesaCallbackView.as_view(), name='c2b_callback'),
]
