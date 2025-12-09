# meters/views.py
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.exceptions import ValidationError 
from django.shortcuts import get_object_or_404

from .models import Meter, MeterAssignment
from .serializers import MeterSerializer, MeterAssignmentSerializer, MeterQuerySerializer
from core.permissions import IsClientMember
from integrations.stronpower_service import StronpowerService
from core.schema_serializers import MessageSerializer, MeterQueryRequestSerializer


class MeterListCreateView(generics.ListCreateAPIView):
    """List and create meters"""
    serializer_class = MeterSerializer
    permission_classes = [IsAuthenticated, IsClientMember]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'meter_type', 'client']
    search_fields = ['meter_id', 'location']
    ordering_fields = ['created_at', 'meter_id']
    ordering = ['-created_at']

    queryset = Meter.objects.select_related('client').all()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Meter.objects.none()
        user = self.request.user
        if getattr(user, "is_system_admin", False):
            return self.queryset
        return self.queryset.filter(client_id=getattr(user, "client_id", None))

    def perform_create(self, serializer):
        """
        When creating a meter:
        - If system admin: require client in payload
        - If normal client user: force client = request.user.client
        """
        user = self.request.user

        if getattr(user, "is_system_admin", False):
            client = serializer.validated_data.get("client")
            if client is None:
                raise ValidationError({"client": "This field is required for system admin."})
            serializer.save()
        else:
            if not getattr(user, "client", None):
                raise ValidationError({"client": "User is not linked to any client."})
            serializer.save(client=user.client)



class MeterRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, delete meter"""
    serializer_class = MeterSerializer
    permission_classes = [IsAuthenticated, IsClientMember]
    queryset = Meter.objects.select_related('client').all()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Meter.objects.none()
        user = self.request.user
        if getattr(user, "is_system_admin", False):
            return self.queryset
        return self.queryset.filter(client_id=getattr(user, "client_id", None))


class MeterQueryView(APIView):
    """Query meter status from Stronpower"""
    permission_classes = [IsAuthenticated, IsClientMember]

    @extend_schema(
        tags=["meters"],
        operation_id="meters_query",
        request=MeterQueryRequestSerializer,  # body: meter_id
        responses={
            200: OpenApiResponse(None, description="Stronpower response payload"),
            400: OpenApiResponse(MessageSerializer),
            404: OpenApiResponse(MessageSerializer),
        },
    )
    def post(self, request):
        serializer = MeterQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        meter_id = serializer.validated_data["meter_id"]

        try:
            # also load client to access its Stronpower credentials
            meter = Meter.objects.select_related("client").get(meter_id=meter_id)
            client = meter.client

            # Prefer credentials stored on the client; fall back to your test ones
            credentials = {
                "company_name": getattr(client, "stronpower_company_name", None) or "DicksonAbukal",
                "username": getattr(client, "stronpower_username", None) or "Prepaid",
                "password": getattr(client, "stronpower_password", None) or "147369",
            }

            stronpower = StronpowerService()
            success, data, error = stronpower.query_meter_info(credentials, meter_id)

            if success:
                # If Stronpower returns a list, take the first entry
                payload = data[0] if isinstance(data, list) and data else data
                return Response(payload, status=status.HTTP_200_OK)

            return Response({"error": error or "Vendor error"}, status=status.HTTP_400_BAD_REQUEST)

        except Meter.DoesNotExist:
            return Response({"error": "Meter not found"}, status=status.HTTP_404_NOT_FOUND)



class MeterAssignmentListView(generics.ListAPIView):
    """List meter assignments"""
    serializer_class = MeterAssignmentSerializer
    permission_classes = [IsAuthenticated, IsClientMember]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return MeterAssignment.objects.none()
        meter_id = self.kwargs.get('pk')
        return MeterAssignment.objects.filter(
            meter_id=meter_id,
            is_active=True
        ).select_related('meter', 'customer')


class MeterSuspendView(APIView):
    """
    Soft-suspend a meter in our system.
    (Optional: later call Stronpower's stop/suspend API if they expose one.)
    """
    permission_classes = [IsAuthenticated, IsClientMember]

    def post(self, request, pk):
        user = request.user

        qs = Meter.objects.select_related("client").all()
        if not getattr(user, "is_system_admin", False):
            qs = qs.filter(client_id=getattr(user, "client_id", None))

        meter = get_object_or_404(qs, pk=pk)

        meter.status = "suspended"
        meter.save(update_fields=["status"])

        return Response(
            {"message": "Meter suspended successfully"},
            status=status.HTTP_200_OK,
        )
        
        
class MeterResumeView(APIView):
    """
    Resume a previously suspended meter (set status back to 'active').
    """
    permission_classes = [IsAuthenticated, IsClientMember]

    def post(self, request, pk):
        user = request.user

        qs = Meter.objects.select_related("client").all()
        if not getattr(user, "is_system_admin", False):
            qs = qs.filter(client_id=getattr(user, "client_id", None))

        meter = get_object_or_404(qs, pk=pk)

        meter.status = "active"
        meter.save(update_fields=["status"])

        return Response(
            {"message": "Meter resumed successfully"},
            status=status.HTTP_200_OK,
        )
