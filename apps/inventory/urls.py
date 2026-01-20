from django.urls import path
from apps.inventory.views import (
    InventoryBatchListCreate, InventoryBatchRetrieveUpdateDestroy,
    InventoryMovementListCreate, StockAdjustmentView,
    AuditLogListView, StockSyncView, ExpiredBatchesView, InventorySummaryView
)

app_name = 'inventory'

urlpatterns = [
    # Summary endpoint
    path('summary/', InventorySummaryView.as_view(), name='inventory-summary'),
    
    # Batch endpoints
    path('batches/', InventoryBatchListCreate.as_view(), name='batch-list-create'),
    path('batches/<int:pk>/', InventoryBatchRetrieveUpdateDestroy.as_view(), name='batch-detail'),
    
    # Movement endpoints
    path('movements/', InventoryMovementListCreate.as_view(), name='movement-list-create'),
    
    # Stock adjustment
    path('adjust-stock/', StockAdjustmentView.as_view(), name='stock-adjust'),
    
    # Audit and sync endpoints
    path('audit-logs/', AuditLogListView.as_view(), name='audit-logs'),
    path('sync-stock/', StockSyncView.as_view(), name='stock-sync'),
    path('expired-batches/', ExpiredBatchesView.as_view(), name='expired-batches'),
]
