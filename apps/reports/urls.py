from django.urls import path
from .views import (
    SalesReportView,
    InventoryReportView,
    TaxReportView,
    ProfitLossReportView,
    ExportReportView
)

urlpatterns = [
    path('sales/', SalesReportView.as_view(), name='sales-report'),
    path('inventory/', InventoryReportView.as_view(), name='inventory-report'),
    path('tax/', TaxReportView.as_view(), name='tax-report'),
    path('profit-loss/', ProfitLossReportView.as_view(), name='profit-loss-report'),
    path('export/', ExportReportView.as_view(), name='export-report'),
]
