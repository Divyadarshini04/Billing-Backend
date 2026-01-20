from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

User = get_user_model()

class CustomUserAdmin(BaseUserAdmin):
    model = User
    list_display = ("id", "phone", "is_staff", "is_superuser")
    list_filter = ("is_staff", "is_superuser")
    search_fields = ("phone",)
    ordering = ("id",)

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone", "password1", "password2", "is_staff", "is_superuser", "groups"),
        }),
    )

admin.site.register(User, CustomUserAdmin)
