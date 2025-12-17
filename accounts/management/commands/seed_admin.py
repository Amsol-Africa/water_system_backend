# backend/accounts/management/commands/seed_admin.py

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = "Seed a default system admin user"

    def handle(self, *args, **kwargs):
        email = "admin@amsol.com"
        password = "password123"

        # check if exists
        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING("Admin user already exists"))
            return

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name="Admin",
            last_name="User",
            role="system_admin",
            is_active=True,
        )

        self.stdout.write(self.style.SUCCESS(f"Admin user created: {email}"))
