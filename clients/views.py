# clients/views.py
from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count, Sum
from drf_spectacular.utils import extend_schema

from .models import Client
from .serializers import ClientSerializer, ClientStatsSerializer
from core.permissions import IsSystemAdmin, IsClientAdminOrSystemAdmin


class ClientListCreateView(generics.ListCreateAPIView):
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated, IsSystemAdmin]
    queryset = Client.objects.annotate(
        meters_count=Count('meters'),
        customers_count=Count('customers'),
        users_count=Count('users')
    )

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Client.objects.none()
        return super().get_queryset()


class ClientRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated, IsClientAdminOrSystemAdmin]
    queryset = Client.objects.all()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Client.objects.none()
        user = self.request.user
        if getattr(user, "is_system_admin", False):
            return self.queryset
        return self.queryset.filter(id=getattr(user, "client_id", None))


@extend_schema(
    responses=ClientStatsSerializer,
    tags=["clients"],
    operation_id="clients_stats",
)
class ClientStatsView(APIView):
    permission_classes = [IsAuthenticated, IsClientAdminOrSystemAdmin]

    @extend_schema(
        tags=["clients"],
        operation_id="clients_stats",
        responses=ClientStatsSerializer,
    )
    def get(self, request, pk):
        client = Client.objects.get(pk=pk)
        stats = {
            'total_meters': client.meters.count(),
            'active_meters': client.meters.filter(status='active').count(),
            'total_customers': client.customers.count(),
            'total_tokens': client.meters.aggregate(total=Count('tokens'))['total'] or 0,
            'total_payments': client.payments.aggregate(total=Sum('amount'))['total'] or 0,
            'recent_alerts': client.alerts.filter(is_acknowledged=False).count(),
        }
        serializer = ClientStatsSerializer(stats)
        return Response(serializer.data)
