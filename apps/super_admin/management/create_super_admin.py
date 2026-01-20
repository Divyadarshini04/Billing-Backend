from django.core.management.base import BaseCommand
from apps.users.models import User


class Command(BaseCommand):
    help = "Create default Super Admin"

    def handle(self, *args, **options):
        phone = "9342547471"
        password = "Admin@123"

        if User.objects.filter(phone=phone).exists():
            self.stdout.write(self.style.WARNING("Super Admin already exists"))
            return

        user = User.objects.create(
            phone=phone,
            role="SUPER_ADMIN",
            is_active=True,
            is_staff=True,
            is_superuser=True
        )
        user.set_password(password)
        user.save()

        self.stdout.write(self.style.SUCCESS("Super Admin created successfully"))
