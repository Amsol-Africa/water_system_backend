# ============================================
#  payments/urls.py
# ============================================
from django.urls import path
from . import views
from .webhook_views import MPesaC2BValidationView, MPesaC2BConfirmationView

app_name = "payments"

urlpatterns = [
    # Authenticated endpoints
    path("", views.PaymentListView.as_view(), name="payment_list"),
    path("<uuid:pk>/", views.PaymentRetrieveView.as_view(), name="payment_detail"),
    path("<uuid:pk>/retry/", views.PaymentRetryView.as_view(), name="payment_retry"),
    path("reconcile/", views.PaymentReconcileView.as_view(), name="payment_reconcile"),

    # Public M-Pesa C2B endpoints (Daraja calls these)
    path(
        "webhooks/c2b/validation/",
        MPesaC2BValidationView.as_view(),
        name="c2b_validation",
    ),
    path(
        "webhooks/c2b/confirmation/",
        MPesaC2BConfirmationView.as_view(),
        name="c2b_confirmation",
    ),
]
