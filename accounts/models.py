# ============================================
# FILE 2: accounts/models.py - User Model
# ============================================
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
import uuid


class UserManager(BaseUserManager):
    """Custom user manager"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.SYSTEM_ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom User model with role-based access"""
    
    SYSTEM_ADMIN = 'system_admin'
    CLIENT_ADMIN = 'client_admin'
    OPERATOR = 'operator'
    FIELD_ENGINEER = 'field_engineer'
    READ_ONLY = 'read_only'
    
    ROLE_CHOICES = [
        (SYSTEM_ADMIN, 'System Admin'),
        (CLIENT_ADMIN, 'Client Admin'),
        (OPERATOR, 'Operator'),
        (FIELD_ENGINEER, 'Field Engineer'),
        (READ_ONLY, 'Read Only Viewer'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None  # Remove username field
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=OPERATOR)
    phone = models.CharField(max_length=20, blank=True)
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='users'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = UserManager()
    
    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"
    
    @property
    def is_system_admin(self):
        return self.role == self.SYSTEM_ADMIN
    
    @property
    def is_client_admin(self):
        return self.role == self.CLIENT_ADMIN