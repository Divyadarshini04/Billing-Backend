from django.contrib import admin
from .models import Invoice, InvoiceItem, InvoiceReturn

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'customer', 'total_amount', 'paid_amount', 'payment_status', 'status', 'invoice_date')
    list_filter = ('status', 'payment_status', 'billing_mode', 'invoice_date')
    search_fields = ('invoice_number', 'customer__name')
    readonly_fields = ('invoice_number', 'created_at', 'updated_at')
    fieldsets = (
        ('Invoice Details', {'fields': ('invoice_number', 'customer', 'billing_mode', 'status')}),
        ('Amounts', {'fields': ('subtotal', 'discount_amount', 'discount_percent', 'cgst_amount', 'sgst_amount', 'igst_amount', 'total_amount')}),
        ('Payment', {'fields': ('paid_amount', 'payment_status')}),
        ('Additional', {'fields': ('notes', 'created_at', 'updated_at')}),
    )

@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'invoice', 'quantity', 'unit_price', 'line_total')
    list_filter = ('created_at',)
    search_fields = ('product_name', 'invoice__invoice_number')

@admin.register(InvoiceReturn)
class InvoiceReturnAdmin(admin.ModelAdmin):
    list_display = ('return_number', 'invoice', 'return_amount', 'status')
    list_filter = ('status', 'created_at')
    search_fields = ('return_number', 'invoice__invoice_number')
    readonly_fields = ('return_number', 'created_at', 'updated_at')
