from django.contrib import admin
from .models import SystemSettings, ActivityLog, Unit

@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Company Information", {
            "fields": ("company_name", "support_email")
        }),
        ("Settings", {
            "fields": ("currency", "gst_percentage")
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    readonly_fields = ("created_at", "updated_at")

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("user", "action", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("user__phone", "user__first_name", "description")
    readonly_fields = ("user", "action", "description", "ip_address", "user_agent", "created_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("name", "symbol", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "symbol")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Unit Information", {
            "fields": ("name", "symbol", "description")
        }),
        ("Status", {
            "fields": ("is_active",)
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
