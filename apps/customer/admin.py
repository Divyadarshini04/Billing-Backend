from django.contrib import admin
from .models import Customer, CustomerAddress, LoyaltyTransaction

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'customer_type', 'status', 'loyalty_tier', 'loyalty_points')
    list_filter = ('status', 'customer_type', 'loyalty_tier', 'created_at')
    search_fields = ('name', 'phone', 'email', 'gstin')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {'fields': ('name', 'phone', 'email')}),
        ('Tax Information', {'fields': ('gstin',)}),
        ('Customer Settings', {'fields': ('customer_type', 'status')}),
        ('Credit & Loyalty', {'fields': ('credit_limit', 'current_credit_used', 'loyalty_points', 'loyalty_tier')}),
        ('Additional', {'fields': ('notes', 'created_at', 'updated_at')}),
    )

@admin.register(CustomerAddress)
class CustomerAddressAdmin(admin.ModelAdmin):
    list_display = ('customer', 'type', 'city', 'state', 'is_default')
    list_filter = ('type', 'is_default')
    search_fields = ('customer__name', 'city', 'state')

@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    list_display = ('customer', 'transaction_type', 'points', 'description', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('customer__name', 'description')
    readonly_fields = ('created_at',)
