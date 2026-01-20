from django.urls import path
from apps.purchase.views import (
    SupplierListCreate, SupplierRetrieveUpdateDestroy,
    PurchaseOrderListCreate, PurchaseOrderRetrieveUpdate,
    PurchaseOrderItemListCreate, PurchaseOrderItemRetrieveUpdateDestroy,
    PurchaseOrderApproveView, PurchaseReceiptCreateView,
    PaymentRecordListCreate, DirectStockInwardView
)

app_name = 'purchase'

urlpatterns = [
    path('suppliers/', SupplierListCreate.as_view(), name='supplier-list-create'),
    path('suppliers/<int:pk>/', SupplierRetrieveUpdateDestroy.as_view(), name='supplier-detail'),

    path('orders/', PurchaseOrderListCreate.as_view(), name='order-list-create'),
    path('orders/<int:pk>/', PurchaseOrderRetrieveUpdate.as_view(), name='order-detail'),
    path('orders/<int:pk>/approve/', PurchaseOrderApproveView.as_view(), name='order-approve'),
    
    path('items/', PurchaseOrderItemListCreate.as_view(), name='item-list-create'),
    path('items/<int:pk>/', PurchaseOrderItemRetrieveUpdateDestroy.as_view(), name='item-detail'),

    path('receipts/', PurchaseReceiptCreateView.as_view(), name='receipt-list-create'),
    
    path('payments/', PaymentRecordListCreate.as_view(), name='payment-list-create'),
    path('direct-inward/', DirectStockInwardView.as_view(), name='direct-stock-inward'),
]
