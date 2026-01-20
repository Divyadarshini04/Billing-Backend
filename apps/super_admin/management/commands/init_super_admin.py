from django.core.management.base import BaseCommand
from django.db import IntegrityError
from apps.auth_app.models import User
from apps.super_admin.models import SystemSettings, Unit

class Command(BaseCommand):
    help = "Initialize Super Admin user and system settings"

    def add_arguments(self, parser):
        parser.add_argument(
            "--phone",
            type=str,
            default="9876543210",
            help="Phone number for super admin user",
        )
        parser.add_argument(
            "--name",
            type=str,
            default="Super Admin",
            help="Name for super admin user",
        )
        parser.add_argument(
            "--email",
            type=str,
            default="admin@billapp.com",
            help="Email for super admin user",
        )

    def handle(self, *args, **options):
        phone = options["phone"]
        name = options["name"]
        email = options["email"]

        # Create Super Admin User
        try:
            user, created = User.objects.get_or_create(
                phone=phone,
                defaults={
                    "first_name": name,
                    "email": email,
                    "is_super_admin": True,
                    "is_active": True,
                },
            )

            if created:
                user.set_password("admin123")  # Default password - user should change it
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Super Admin user created successfully!\n"
                        f"  Phone: {phone}\n"
                        f"  Name: {name}\n"
                        f"  Email: {email}\n"
                        f"  Default Password: admin123 (Change this!)"
                    )
                )
            else:
                if not user.is_super_admin:
                    user.is_super_admin = True
                    user.save()
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠ Super Admin user already exists (Phone: {phone})"
                    )
                )

        except IntegrityError as e:
            self.stdout.write(self.style.ERROR(f"✗ Error creating user: {e}"))
            return

        # Initialize System Settings
        settings, created = SystemSettings.objects.get_or_create(
            pk=1,
            defaults={
                "company_name": "Billing Application",
                "support_email": email,
                "currency": "INR",
                "gst_percentage": 18.00,
                "tax_percentage": 5.00,
            },
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    "✓ System settings initialized successfully!\n"
                    "  Company: Billing Application\n"
                    "  Currency: INR\n"
                    "  GST: 18%\n"
                    "  Tax: 5%"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING("⚠ System settings already exist")
            )

        # Initialize Default Units
        default_units = [
            {"name": "Kilogram", "symbol": "kg", "description": "Weight in kilograms"},
            {"name": "Gram", "symbol": "g", "description": "Weight in grams"},
            {"name": "Liter", "symbol": "L", "description": "Volume in liters"},
            {"name": "Milliliter", "symbol": "ml", "description": "Volume in milliliters"},
            {"name": "Piece", "symbol": "pc", "description": "Individual piece or unit"},
            {"name": "Box", "symbol": "box", "description": "Box/Package"},
            {"name": "Dozen", "symbol": "dz", "description": "Group of 12 items"},
            {"name": "Meter", "symbol": "m", "description": "Length in meters"},
            {"name": "Centimeter", "symbol": "cm", "description": "Length in centimeters"},
        ]

        created_units = []
        for unit_data in default_units:
            unit, created = Unit.objects.get_or_create(
                name=unit_data["name"],
                defaults={
                    "symbol": unit_data["symbol"],
                    "description": unit_data["description"],
                    "is_active": True,
                },
            )
            if created:
                created_units.append(unit.name)

        if created_units:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Default units initialized successfully! ({len(created_units)} new units)\n"
                    f"  {', '.join(created_units)}"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING("⚠ Default units already exist")
            )

        self.stdout.write(
            self.style.SUCCESS(
                "\n" + "="*60
                + "\n✓ Super Admin initialization completed successfully!\n"
                + "="*60
            )
        )
