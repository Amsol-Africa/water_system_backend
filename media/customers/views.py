# customers/views.py
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import Customer
from meters.models import Meter, MeterAssignment
from .serializers import CustomerSerializer, CustomerAssignMeterSerializer
from core.permissions import IsClientMember
from core.schema_serializers import (
    MessageSerializer,
    AssignMeterRequestSerializer,
    UnassignMeterRequestSerializer,
)


class CustomerListCreateView(generics.ListCreateAPIView):
    """List and create customers"""
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated, IsClientMember]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active', 'client']
    search_fields = ['name', 'phone', 'email', 'customer_id']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']

    queryset = Customer.objects.select_related('client').all()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Customer.objects.none()
        user = self.request.user
        if getattr(user, "is_system_admin", False):
            return self.queryset
        return self.queryset.filter(client_id=getattr(user, "client_id", None))

    def perform_create(self, serializer):
        """
        Automatically attach the logged-in user's client and
        generate a customer_id if not provided.
        """
        user = self.request.user

        # Determine client
        if getattr(user, "is_system_admin", False):
            client = serializer.validated_data.get("client") or user.client
        else:
            client = user.client

        if client is None:
            # This is the error you saw earlier
            raise ValidationError({"client": "User is not attached to any client"})

        # Generate customer_id if missing
        customer_id = serializer.validated_data.get("customer_id")
        if not customer_id:
            prefix = (client.name or "CUST")[:3].upper()
            last = Customer.objects.filter(client=client).order_by('-created_at').first()
            next_num = 1
            if last and last.customer_id and "-" in last.customer_id:
                try:
                    next_num = int(last.customer_id.split("-")[-1]) + 1
                except ValueError:
                    next_num = 1
            customer_id = f"{prefix}-{next_num:05d}"

        serializer.save(client=client, customer_id=customer_id)



class CustomerRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, delete customer"""
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated, IsClientMember]
    queryset = Customer.objects.select_related('client').all()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Customer.objects.none()
        user = self.request.user
        if getattr(user, "is_system_admin", False):
            return self.queryset
        return self.queryset.filter(client_id=getattr(user, "client_id", None))


class CustomerAssignMeterView(APIView):
    """Assign meter to customer"""
    permission_classes = [IsAuthenticated, IsClientMember]

    @extend_schema(
        tags=["customers"],
        operation_id="customers_assign_meter",
        request=AssignMeterRequestSerializer,     # docs can stay as UUID for now
        responses={
            201: OpenApiResponse(MessageSerializer),
            400: OpenApiResponse(MessageSerializer),
            404: OpenApiResponse(MessageSerializer),
        },
    )
    def post(self, request, pk):
        serializer = CustomerAssignMeterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        raw_meter_id = serializer.validated_data["meter_id"]

        # 1) Load customer (respect client permissions)
        try:
            customer = Customer.objects.get(pk=pk)
        except Customer.DoesNotExist:
            return Response(
                {"error": "Customer not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 2) Resolve meter by PK or by meter_id
        meter = None

        # Try as UUID PK
        try:
            meter = Meter.objects.select_related("client").get(pk=raw_meter_id)
        except (ValueError, Meter.DoesNotExist):
            # Not a valid UUID or no meter with that PK -> try by meter_id
            meter = (
                Meter.objects.select_related("client")
                .filter(meter_id=raw_meter_id)
                .first()
            )

        if not meter:
            return Response(
                {"error": "Meter not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 3) Ensure meter belongs to same client as customer
        if meter.client_id != customer.client_id:
            return Response(
                {"error": "Meter does not belong to this client"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 4) Check if already assigned
        existing_assignment = (
            MeterAssignment.objects
            .filter(meter=meter, is_active=True)
            .select_related("customer")
            .first()
        )

        if existing_assignment:
            if existing_assignment.customer_id == customer.id:
                return Response(
                    {"error": "Meter already assigned to this customer"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                return Response(
                    {
                        "error": f"Meter already assigned to customer "
                                 f"{existing_assignment.customer.name}"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # 5) Create assignment
        MeterAssignment.objects.create(meter=meter, customer=customer)

        return Response(
            {"message": "Meter assigned successfully"},
            status=status.HTTP_201_CREATED,
        )

class CustomerUnassignMeterView(APIView):
    """Unassign meter from customer"""
    permission_classes = [IsAuthenticated, IsClientMember]

    @extend_schema(
        tags=["customers"],
        operation_id="customers_unassign_meter",
        request=UnassignMeterRequestSerializer,   # body expects meter_id
        responses={
            200: OpenApiResponse(MessageSerializer),
            404: OpenApiResponse(MessageSerializer),
        },
    )
    def post(self, request, pk):
        serializer = CustomerAssignMeterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        raw_meter_id = serializer.validated_data["meter_id"]

        # Resolve meter (same logic as assign)
        meter = None
        try:
            meter = Meter.objects.get(pk=raw_meter_id)
        except (ValueError, Meter.DoesNotExist):
            meter = Meter.objects.filter(meter_id=raw_meter_id).first()

        if not meter:
            return Response(
                {"error": "Meter not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            assignment = MeterAssignment.objects.get(
                meter_id=meter.id,  # FK pk
                customer_id=pk,
                is_active=True,
            )
            assignment.is_active = False
            assignment.deactivated_on = timezone.now()
            assignment.save()
            return Response(
                {"message": "Meter unassigned successfully"},
                status=status.HTTP_200_OK,
            )
        except MeterAssignment.DoesNotExist:
            return Response(
                {"error": "Assignment not found"},
                status=status.HTTP_404_NOT_FOUND,
            )