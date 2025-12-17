# ============================================
# FILE: tokens/views.py
# ============================================
from decimal import Decimal, InvalidOperation

from django.shortcuts import render
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Token
from meters.models import Meter
from .services import _send_token_sms
from customers.models import Customer
from .serializers import (
    TokenSerializer, IssueTokenSerializer,
    ClearCreditSerializer, ClearTamperSerializer
)
from core.permissions import IsClientMember
from integrations.stronpower_service import StronpowerService


class TokenListView(generics.ListAPIView):
    """List tokens"""
    serializer_class = TokenSerializer
    permission_classes = [IsAuthenticated, IsClientMember]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'token_type', 'meter', 'customer']
    search_fields = [
        'token_value',
        'meter__meter_id',
        'customer__name',
        'customer__phone',
        'payment__mpesa_transaction_id',
    ]
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        if user.is_system_admin:
            return Token.objects.select_related('meter', 'customer', 'issued_by').all()
        return Token.objects.filter(
            meter__client_id=user.client_id
        ).select_related('meter', 'customer', 'issued_by')


class TokenRetrieveView(generics.RetrieveAPIView):
    """Retrieve token"""
    serializer_class = TokenSerializer
    permission_classes = [IsAuthenticated, IsClientMember]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_system_admin:
            return Token.objects.select_related('meter', 'customer', 'issued_by').all()
        return Token.objects.filter(
            meter__client_id=user.client_id
        ).select_related('meter', 'customer', 'issued_by')


class IssueTokenView(APIView):
    """Issue a vending token (manual vending from the UI)"""
    permission_classes = [IsAuthenticated, IsClientMember]
    
    def post(self, request):
        serializer = IssueTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            meter = Meter.objects.get(pk=serializer.validated_data['meter_id'])
            customer = Customer.objects.get(pk=serializer.validated_data['customer_id'])
            
            # Get Stronpower credentials
            credentials = {
                'company_name': meter.client.stronpower_company_name,
                'username': meter.client.stronpower_username,
                'password': meter.client.stronpower_password
            }
            
            # Call Stronpower API
            stronpower = StronpowerService()
            success, vend_payload, error = stronpower.vending_meter(
                client_credentials=credentials,
                meter_id=meter.meter_id,
                amount=serializer.validated_data['amount'],
                is_vend_by_unit=serializer.validated_data['is_vend_by_unit'],
                customer_id=customer.customer_id
            )

            token_value = None
            units = None

            if success and vend_payload:
                # Same shape as in vend_and_create_token_for_payment:
                # usually a list with a single dict.
                payload_obj = vend_payload
                if isinstance(payload_obj, list) and payload_obj:
                    payload_obj = payload_obj[0]

                if isinstance(payload_obj, dict):
                    token_value = (
                        payload_obj.get("Token")
                        or payload_obj.get("token")
                        or payload_obj.get("TokenNo")
                        or payload_obj.get("TokenNo1")
                    )
                    raw_units = (
                        payload_obj.get("Total_unit")
                        or payload_obj.get("total_unit")
                        or payload_obj.get("Units")
                        or payload_obj.get("units")
                    )
                    if raw_units is not None:
                        try:
                            units = Decimal(str(raw_units))
                        except (InvalidOperation, TypeError):
                            units = None
                else:
                    token_value = str(payload_obj)

            if not success or not token_value:
                return Response(
                    {'error': error or 'Vending failed'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create token record
            token = Token.objects.create(
                token_value=token_value,
                token_type=Token.VENDING,
                meter=meter,
                customer=customer,
                amount=serializer.validated_data['amount'],
                units=units,
                is_vend_by_unit=serializer.validated_data['is_vend_by_unit'],
                issued_by=request.user,
                status=Token.CREATED
            )

            # 🔔 Send SMS with token
            sms_ok = _send_token_sms(token)
            if sms_ok and token.status != Token.DELIVERED:
                token.status = Token.DELIVERED
                token.delivered_at = timezone.now()
                token.save(update_fields=["status", "delivered_at"])
            
            return Response(
                TokenSerializer(token).data,
                status=status.HTTP_201_CREATED
            )
        
        except (Meter.DoesNotExist, Customer.DoesNotExist):
            return Response(
                {'error': 'Meter or Customer not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class ClearCreditView(APIView):
    """Clear credit token"""
    permission_classes = [IsAuthenticated, IsClientMember]
    
    def post(self, request):
        serializer = ClearCreditSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            meter = Meter.objects.get(pk=serializer.validated_data['meter_id'])
            customer = Customer.objects.get(pk=serializer.validated_data['customer_id'])
            
            credentials = {
                'company_name': meter.client.stronpower_company_name,
                'username': meter.client.stronpower_username,
                'password': meter.client.stronpower_password
            }
            
            stronpower = StronpowerService()
            success, token_value, error = stronpower.clear_credit(
                client_credentials=credentials,
                meter_id=meter.meter_id,
                customer_id=customer.customer_id
            )
            
            if success:
                token = Token.objects.create(
                    token_value=token_value,
                    token_type=Token.CLEAR_CREDIT,
                    meter=meter,
                    customer=customer,
                    issued_by=request.user,
                    status=Token.CREATED,
                )

                # 🔔 SMS
                sms_ok = _send_token_sms(token)
                if sms_ok and token.status != Token.DELIVERED:
                    token.status = Token.DELIVERED
                    token.delivered_at = timezone.now()
                    token.save(update_fields=["status", "delivered_at"])
                
                return Response(
                    TokenSerializer(token).data,
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
        
        except (Meter.DoesNotExist, Customer.DoesNotExist):
            return Response(
                {'error': 'Meter or Customer not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class ClearTamperView(APIView):
    """Clear tamper token"""
    permission_classes = [IsAuthenticated, IsClientMember]
    
    def post(self, request):
        serializer = ClearTamperSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            meter = Meter.objects.get(pk=serializer.validated_data['meter_id'])
            customer = Customer.objects.get(pk=serializer.validated_data['customer_id'])
            
            credentials = {
                'company_name': meter.client.stronpower_company_name,
                'username': meter.client.stronpower_username,
                'password': meter.client.stronpower_password
            }
            
            stronpower = StronpowerService()
            success, token_value, error = stronpower.clear_tamper(
                client_credentials=credentials,
                meter_id=meter.meter_id,
                customer_id=customer.customer_id
            )
            
            if success:
                token = Token.objects.create(
                    token_value=token_value,
                    token_type=Token.CLEAR_TAMPER,
                    meter=meter,
                    customer=customer,
                    issued_by=request.user,
                    status=Token.CREATED,
                )

                # SMS
                sms_ok = _send_token_sms(token)
                if sms_ok and token.status != Token.DELIVERED:
                    token.status = Token.DELIVERED
                    token.delivered_at = timezone.now()
                    token.save(update_fields=["status", "delivered_at"])
                
                return Response(
                    TokenSerializer(token).data,
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
        
        except (Meter.DoesNotExist, Customer.DoesNotExist):
            return Response(
                {'error': 'Meter or Customer not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
            
class TokenResendSmsView(APIView):
    """
    Resend SMS for an existing token.
    Uses the same _send_token_sms helper and, on success,
    marks token as DELIVERED (if not already) and sets delivered_at.
    """
    permission_classes = [IsAuthenticated, IsClientMember]

    def post(self, request, pk):
        user = request.user

        # Respect client scoping just like in TokenList / Retrieve
        qs = Token.objects.select_related("meter", "customer", "issued_by")
        if not getattr(user, "is_system_admin", False):
            qs = qs.filter(meter__client_id=getattr(user, "client_id", None))

        try:
            token = qs.get(pk=pk)
        except Token.DoesNotExist:
            return Response(
                {"error": "Token not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not token.customer or not token.customer.phone:
            return Response(
                {"error": "Token does not have a customer phone to send SMS to"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sms_ok = _send_token_sms(token)

        # If SMS sent successfully, mark as delivered
        if sms_ok and token.status != Token.DELIVERED:
            token.status = Token.DELIVERED
            token.delivered_at = timezone.now()
            token.save(update_fields=["status", "delivered_at"])

        return Response(
            {
                "success": bool(sms_ok),
                "message": "SMS resent successfully" if sms_ok else "Failed to send SMS",
                "token": TokenSerializer(token).data,
            },
            status=status.HTTP_200_OK if sms_ok else status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
