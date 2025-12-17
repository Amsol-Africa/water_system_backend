# accounts/views.py
from django.contrib.auth import get_user_model
from rest_framework import generics, status, serializers
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from .serializers import UserSerializer, LoginSerializer
from core.permissions import IsSystemAdmin
from core.schema_serializers import (
    MessageSerializer,
    TokenPairSerializer,
    LogoutRequestSerializer,
)

User = get_user_model()


class LoginView(APIView):
    """User login view"""
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    @extend_schema(
        tags=["auth"],
        operation_id="auth_login",
        request=LoginSerializer,
        responses={200: OpenApiResponse(TokenPairSerializer, description="JWT pair and current user"),
                   400: OpenApiResponse(MessageSerializer, description="Validation error")},
        examples=[
            OpenApiExample(
                "Login success",
                value={
                    "access": "<jwt-access>",
                    "refresh": "<jwt-refresh>",
                    "user": {
                        "id": 1, "email": "admin@example.com",
                        "first_name": "Admin", "last_name": "User",
                        "role": "system_admin", "phone": "+254700000000",
                        "client": None, "client_name": None, "is_active": True,
                        "date_joined": "2025-10-01T10:00:00Z",
                        "last_login": "2025-10-30T07:00:00Z",
                        "created_at": "2025-10-01T10:00:00Z",
                        "updated_at": "2025-10-30T07:00:00Z"
                    }
                },
            )
        ],
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        })


class LogoutView(APIView):
    """User logout view"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["auth"],
        operation_id="auth_logout",
        request=LogoutRequestSerializer,
        responses={200: OpenApiResponse(MessageSerializer, description="Logout message")},
    )
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
        except Exception:
            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)


class CurrentUserView(generics.RetrieveAPIView):
    """Get current authenticated user"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["users"], operation_id="me_read", responses=UserSerializer)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_object(self):
        return self.request.user


class UserListCreateView(generics.ListCreateAPIView):
    """List and create users"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsSystemAdmin]

    @extend_schema(operation_id="users_list")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(operation_id="users_create")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return User.objects.none()
        return User.objects.select_related('client').all()


class UserRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, delete user"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsSystemAdmin]

    @extend_schema(operation_id="users_read")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(operation_id="users_update")
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(operation_id="users_partial_update")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(operation_id="users_delete")
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return User.objects.none()
        return User.objects.select_related('client').all()
