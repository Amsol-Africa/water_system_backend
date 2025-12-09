# ============================================
# FILE 5: payments/views.py (FINAL)
# ============================================
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import PaymentNotification
from .serializers import PaymentNotificationSerializer
from core.permissions import IsClientMember

from meters.models import Meter
from tokens.services import vend_and_create_token_for_payment
from tokens.models import Token
from tokens.serializers import TokenSerializer
from core.sms_service import SMSService


class PaymentListView(generics.ListAPIView):
    """List payments"""
    serializer_class = PaymentNotificationSerializer
    permission_classes = [IsAuthenticated, IsClientMember]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'client']
    search_fields = ['mpesa_transaction_id', 'phone', 'account_number']
    ordering_fields = ['received_at', 'amount']
    ordering = ['-received_at']

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "is_system_admin", False):
            return PaymentNotification.objects.select_related("client", "customer").all()
        return (
            PaymentNotification.objects
            .filter(client_id=getattr(user, "client_id", None))
            .select_related("client", "customer")
        )


class PaymentRetrieveView(generics.RetrieveAPIView):
    """Retrieve single payment"""
    serializer_class = PaymentNotificationSerializer
    permission_classes = [IsAuthenticated, IsClientMember]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "is_system_admin", False):
            return PaymentNotification.objects.select_related("client", "customer").all()
        return (
            PaymentNotification.objects
            .filter(client_id=getattr(user, "client_id", None))
            .select_related("client", "customer")
        )


class PaymentRetryView(APIView):
    """
    Retry failed payment:
    - Re-run vending via Stronpower (idempotent on mpesa_transaction_id)
    - Re-send SMS with token
    """
    permission_classes = [IsAuthenticated, IsClientMember]

    def post(self, request, pk):
        user = request.user

        qs = PaymentNotification.objects.all()
        if not getattr(user, "is_system_admin", False):
            qs = qs.filter(client_id=getattr(user, "client_id", None))

        payment = get_object_or_404(qs, pk=pk)

        if not payment.client:
            return Response(
                {"error": "Payment has no client attached"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Resolve meter from account_number + client
        meter = (
            Meter.objects
            .filter(meter_id=payment.account_number, client=payment.client)
            .first()
        )
        if not meter:
            return Response(
                {"error": "Meter not found for this payment"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        customer = payment.customer
        if not customer:
            return Response(
                {"error": "Payment has no customer attached"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Run same vending flow (idempotent on mpesa_transaction_id)
        success, token, error = vend_and_create_token_for_payment(
            meter=meter,
            customer=customer,
            amount=payment.amount,
            is_vend_by_unit=False, # M-Pesa is amount-based
            payment=payment,
            idempotency_key=payment.mpesa_transaction_id,
        )

        if not success or not token:
            payment.status = PaymentNotification.FAILED
            payment.error_message = error or "Vending failed on retry"
            payment.processed_at = timezone.now()
            payment.save(update_fields=["status", "error_message", "processed_at"])
            return Response(
                {"error": error or "Vending failed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Mark payment VERIFIED if not already
        if payment.status != PaymentNotification.VERIFIED:
            payment.status = PaymentNotification.VERIFIED
            payment.processed_at = timezone.now()
            payment.save(update_fields=["status", "processed_at"])

        # Re-send SMS
        sms = SMSService()
        sms_ok = sms.send_template(
            to_number=customer.phone,
            template_name="token_issued",
            context={
                "meter_id": meter.meter_id,
                "token": token.token_value,
                "amount": payment.amount,
            },
        )

        if sms_ok and token.status != Token.DELIVERED:
            token.status = Token.DELIVERED
            token.delivered_at = timezone.now()
            token.save(update_fields=["status", "delivered_at"])

        return Response(
            {
                "message": "Payment retry successful",
                "sms_sent": sms_ok,
                "token": TokenSerializer(token).data,
            },
            status=status.HTTP_200_OK,
        )


class PaymentReconcileView(APIView):
    """
    Placeholder for bulk reconciliation logic.
    Later: run queries to M-Pesa / Stronpower to reconcile statuses.
    """
    permission_classes = [IsAuthenticated, IsClientMember]

    def post(self, request):
        # TODO: Implement actual reconciliation (Celery task, etc.)
        return Response(
            {"message": "Reconciliation initiated (not yet implemented)"},
            status=status.HTTP_200_OK,
        )
