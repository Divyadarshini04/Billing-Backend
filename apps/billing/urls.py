from django.urls import path
from .views import (
    InvoiceListCreateView,
    InvoiceDetailView,
    InvoiceAddItemView,
    InvoiceCompleteView,
    InvoiceCancelView,
    InvoiceReturnView,
    NextInvoiceNumberView,
    DiscountRuleViewSet,
    DiscountLogViewSet
)
from rest_framework.routers import DefaultRouter
from django.urls import include

router = DefaultRouter()
router.register(r'discount-rules', DiscountRuleViewSet, basename='discount-rules')
router.register(r'discount-logs', DiscountLogViewSet, basename='discount-logs')

urlpatterns = [
    # Invoice endpoints
    path('invoices/next-number/', NextInvoiceNumberView.as_view(), name='next-invoice-number'),
    path('invoices/', InvoiceListCreateView.as_view(), name='invoice-list'),
    path('invoices/<int:pk>/', InvoiceDetailView.as_view(), name='invoice-detail'),
    path('invoices/<int:invoice_id>/items/', InvoiceAddItemView.as_view(), name='invoice-add-items'),
    path('invoices/<int:invoice_id>/complete/', InvoiceCompleteView.as_view(), name='invoice-complete'),
    path('invoices/<int:invoice_id>/cancel/', InvoiceCancelView.as_view(), name='invoice-cancel'),
    path('invoices/<int:invoice_id>/returns/', InvoiceReturnView.as_view(), name='invoice-returns'),
    
    # Discount endpoints
    path('', include(router.urls)),
]
