# alerts/views.py
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import Alert
from .serializers import AlertSerializer, AlertAcknowledgeSerializer
from core.permissions import IsClientMember
from core.schema_serializers import MessageSerializer, AckRequestSerializer


class AlertListView(generics.ListAPIView):
    """List alerts"""
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated, IsClientMember]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['alert_type', 'severity', 'is_acknowledged', 'client']
    search_fields = ['message']
    ordering_fields = ['created_at', 'severity']
    ordering = ['-created_at']

    queryset = Alert.objects.select_related(
        'client', 'meter', 'customer', 'acknowledged_by'
    ).all()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Alert.objects.none()
        user = self.request.user
        if getattr(user, "is_system_admin", False):
            return self.queryset
        return self.queryset.filter(client_id=getattr(user, "client_id", None))


class AlertRetrieveView(generics.RetrieveAPIView):
    """Retrieve alert"""
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated, IsClientMember]
    queryset = Alert.objects.select_related(
        'client', 'meter', 'customer', 'acknowledged_by'
    ).all()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Alert.objects.none()
        user = self.request.user
        if getattr(user, "is_system_admin", False):
            return self.queryset
        return self.queryset.filter(client_id=getattr(user, "client_id", None))


class AlertAcknowledgeView(APIView):
    """Acknowledge an alert"""
    permission_classes = [IsAuthenticated, IsClientMember]

    @extend_schema(
        tags=["alerts"],
        operation_id="alerts_acknowledge",
        request=AckRequestSerializer,  # set to None if you don't take a body
        responses={
            200: OpenApiResponse(AlertSerializer, description="Acknowledged alert"),
            400: OpenApiResponse(MessageSerializer),
            404: OpenApiResponse(MessageSerializer),
        },
    )
    def post(self, request, pk):
        try:
            alert = Alert.objects.select_related(
                'client', 'meter', 'customer', 'acknowledged_by'
            ).get(pk=pk)

            if alert.is_acknowledged:
                return Response({'message': 'Alert already acknowledged'}, status=status.HTTP_400_BAD_REQUEST)

            alert.is_acknowledged = True
            alert.acknowledged_by = request.user
            alert.acknowledged_at = timezone.now()
            alert.save()

            return Response(AlertSerializer(alert).data, status=status.HTTP_200_OK)

        except Alert.DoesNotExist:
            return Response({'error': 'Alert not found'}, status=status.HTTP_404_NOT_FOUND)
