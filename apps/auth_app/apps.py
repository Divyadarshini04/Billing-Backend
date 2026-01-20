from django.apps import AppConfig

class AuthAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.auth_app"

    def ready(self):
        try:
            from apps.auth_app.models import User

            if not User.objects.filter(is_super_admin=True).exists():
                user = User.objects.create(
                    phone="9342547471",
                    is_super_admin=True,
                    is_staff=True,
                    is_active=True
                )
                user.set_password("Admin@123")
                user.save()
                print("✅ Super Admin auto-created")
        except Exception as e:
            print("⚠️ Super Admin auto-create skipped:", e)
