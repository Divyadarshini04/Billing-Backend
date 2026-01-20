from django.contrib import admin
from .models import PaymentMethod, Payment, PaymentRefund

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'requires_gateway')
    list_filter = ('is_active', 'requires_gateway')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_id', 'invoice', 'amount', 'payment_method', 'status', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('payment_id', 'gateway_ref_id', 'invoice__invoice_number')
    readonly_fields = ('payment_id', 'created_at', 'updated_at', 'gateway_response')

@admin.register(PaymentRefund)
class PaymentRefundAdmin(admin.ModelAdmin):
    list_display = ('refund_id', 'payment', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('refund_id', 'payment__payment_id')
    readonly_fields = ('refund_id', 'created_at', 'updated_at')
