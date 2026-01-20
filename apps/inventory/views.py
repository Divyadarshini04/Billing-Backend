from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Q, F, Sum
from django.db import transaction
from django.utils import timezone

from apps.product.models import Product, InventoryBatch, InventoryMovement
from apps.inventory.models import InventoryAuditLog, StockSyncLog
from apps.inventory.serializers import (
    InventoryBatchSerializer, InventoryMovementSerializer,
    InventoryAuditLogSerializer, StockSyncLogSerializer, BatchListSerializer
)
from apps.auth_app.permissions import IsAdminOrHasPermission, IsAuthenticated

class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for inventory endpoints."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class InventoryBatchListCreate(ListCreateAPIView):
    """List and create inventory batches."""
    queryset = InventoryBatch.objects.select_related('product')
    serializer_class = InventoryBatchSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['product_id', 'supplier_id', 'expiry_date']
    search_fields = ['product__name', 'product__product_code', 'batch_number']
    ordering_fields = ['received_at', 'expiry_date', 'remaining_quantity']
    ordering = ['-received_at']
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Use lightweight serializer for list view."""
        if self.request.method == 'GET':
            return BatchListSerializer
        return InventoryBatchSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """Create new batch with permission check."""
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'manage_inventory'):
                return Response(
                    {'detail': 'Permission denied. You do not have inventory management rights.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        batch = serializer.save()
        
        # Log audit
        InventoryAuditLog.objects.create(
            operation_type='batch_create',
            product_id=batch.product_id,
            batch_id=batch.id,
            new_value={'batch_id': batch.id, 'received_quantity': batch.received_quantity},
            user_id=request.user.id if request.user.id else None,
            notes=f"Batch created: {batch.batch_number}"
        )
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class InventoryBatchRetrieveUpdateDestroy(RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete inventory batches."""
    queryset = InventoryBatch.objects.select_related('product')
    serializer_class = InventoryBatchSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Get batch by ID with 404 handling."""
        return get_object_or_404(InventoryBatch, id=self.kwargs['pk'])

    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        """Partial update with permission check."""
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'manage_inventory'):
                return Response(
                    {'detail': 'Permission denied.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        batch = self.get_object()
        old_values = {
            'remaining_quantity': batch.remaining_quantity,
            'batch_number': batch.batch_number
        }
        
        serializer = self.get_serializer(batch, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        batch = serializer.save()
        
        new_values = {
            'remaining_quantity': batch.remaining_quantity,
            'batch_number': batch.batch_number
        }
        
        # Log audit
        if old_values != new_values:
            InventoryAuditLog.objects.create(
                operation_type='batch_update',
                product_id=batch.product_id,
                batch_id=batch.id,
                old_value=old_values,
                new_value=new_values,
                user_id=request.user.id if request.user.id else None
            )
        
        return Response(serializer.data, status=status.HTTP_200_OK)

class InventoryMovementListCreate(ListCreateAPIView):
    """List and create inventory movements (audit trail)."""
    queryset = InventoryMovement.objects.select_related('product', 'batch')
    serializer_class = InventoryMovementSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['product_id', 'change_type', 'reference_type']
    search_fields = ['product__name', 'product__product_code', 'reference_id']
    ordering_fields = ['created_at', 'quantity']
    ordering = ['-created_at']
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """Create movement with inventory update."""
        # Permission check
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'manage_inventory'):
                return Response(
                    {'detail': 'Permission denied.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        product = serializer.validated_data['product']
        quantity = serializer.validated_data['quantity']
        change_type = serializer.validated_data['change_type']
        
        # Update product stock based on movement type
        if change_type in ['purchase', 'return']:
            new_stock = product.stock + abs(quantity)
        else:  # sale, adjustment, damage, transfer
            new_stock = product.stock - abs(quantity)
        
        # Validate sufficient stock for outbound movements
        if new_stock < 0:
            return Response(
                {'detail': 'Insufficient stock for this movement.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Save movement and update stock
        movement = serializer.save(created_by_id=request.user.id if request.user.id else None)
        product.stock = new_stock
        product.save(update_fields=['stock', 'updated_at'])
        
        # Log audit
        InventoryAuditLog.objects.create(
            operation_type='movement_record',
            product_id=product.id,
            batch_id=movement.batch_id,
            new_value={
                'movement_type': change_type,
                'quantity': quantity,
                'new_stock': new_stock
            },
            user_id=request.user.id if request.user.id else None,
            notes=f"{change_type.upper()} movement: {quantity} units"
        )
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class StockAdjustmentView(APIView):
    """Handle manual inventory adjustments."""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """Adjust stock with reason and audit trail."""
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'manage_inventory'):
                return Response(
                    {'detail': 'Permission denied.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        product_id = request.data.get('product_id')
        adjustment_quantity = request.data.get('adjustment_quantity')
        reason = request.data.get('reason', '')

        if not product_id or adjustment_quantity is None:
            return Response(
                {'detail': 'product_id and adjustment_quantity are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        product = get_object_or_404(Product, id=product_id, is_active=True)
        
        old_stock = product.stock
        new_stock = old_stock + adjustment_quantity

        if new_stock < 0:
            return Response(
                {'detail': 'Adjustment would result in negative stock.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        product.stock = new_stock
        product.save(update_fields=['stock', 'updated_at'])

        # Record movement
        InventoryMovement.objects.create(
            product=product,
            change_type='adjustment',
            quantity=adjustment_quantity,
            notes=reason,
            created_by_id=request.user.id if request.user.id else None
        )

        # Log audit
        InventoryAuditLog.objects.create(
            operation_type='stock_adjust',
            product_id=product.id,
            old_value={'stock': old_stock},
            new_value={'stock': new_stock},
            user_id=request.user.id if request.user.id else None,
            notes=f"Adjustment: {adjustment_quantity}. Reason: {reason}"
        )

        return Response(
            {
                'product_id': product.id,
                'old_stock': old_stock,
                'new_stock': new_stock,
                'adjustment': adjustment_quantity
            },
            status=status.HTTP_200_OK
        )

class AuditLogListView(ListAPIView):
    """List inventory audit logs."""
    queryset = InventoryAuditLog.objects.all()
    serializer_class = InventoryAuditLogSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['operation_type', 'product_id', 'batch_id', 'user_id']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    permission_classes = [IsAuthenticated]

class StockSyncView(APIView):
    """Synchronize product stock from batch remaining quantities."""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """Recalculate and sync all product stock from batches."""
        if not request.user.is_superuser:
            return Response(
                {'detail': 'Only superusers can perform stock sync.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        sync_log = StockSyncLog.objects.create(status='in_progress')
        
        try:
            products = Product.objects.filter(is_active=True)
            sync_log.products_count = products.count()
            sync_log.save()
            
            for product in products:
                try:
                    # Calculate total stock from batches
                    total_stock = InventoryBatch.objects.filter(
                        product=product
                    ).aggregate(total=Sum('remaining_quantity'))['total'] or 0
                    
                    old_stock = product.stock
                    product.stock = total_stock
                    product.save(update_fields=['stock', 'updated_at'])
                    
                    if old_stock != total_stock:
                        sync_log.updated_count += 1
                        InventoryAuditLog.objects.create(
                            operation_type='stock_adjust',
                            product_id=product.id,
                            old_value={'stock': old_stock},
                            new_value={'stock': total_stock},
                            user_id=request.user.id if request.user.id else None,
                            notes='Automatic stock sync from batches'
                        )
                
                except Exception as e:
                    sync_log.error_count += 1
                    if not sync_log.error_details:
                        sync_log.error_details = {}
                    sync_log.error_details[str(product.id)] = str(e)
            
            sync_log.status = 'completed'
            sync_log.completed_at = timezone.now()
            sync_log.save()
            
            return Response(
                StockSyncLogSerializer(sync_log).data,
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            sync_log.status = 'failed'
            sync_log.error_details = {'error': str(e)}
            sync_log.completed_at = timezone.now()
            sync_log.save()
            
            return Response(
                {'detail': 'Stock sync failed', 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ExpiredBatchesView(ListAPIView):
    """List expired inventory batches."""
    serializer_class = BatchListSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get batches that are expired."""
        today = timezone.now().date()
        return InventoryBatch.objects.filter(
            expiry_date__lt=today,
            remaining_quantity__gt=0
        ).select_related('product')

class InventorySummaryView(APIView):
    """Get inventory summary with stock status breakdown."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get inventory summary statistics."""
        try:
            # Get all products with their total stock
            products = Product.objects.all()
            
            # Calculate stock status for each product
            in_stock = 0
            low_stock = 0
            out_of_stock = 0
            total_value = 0
            
            for product in products:
                # Get total remaining quantity from batches
                total_qty = InventoryBatch.objects.filter(
                    product=product,
                    remaining_quantity__gt=0
                ).aggregate(total=Sum('remaining_quantity'))['total'] or 0
                
                # Calculate inventory value
                total_value += total_qty * (product.purchase_price or 0)
                
                # Categorize by stock status
                if total_qty > 100:
                    in_stock += 1
                elif total_qty > 0:
                    low_stock += 1
                else:
                    out_of_stock += 1
            
            return Response({
                'total_products': products.count(),
                'in_stock': in_stock,
                'low_stock': low_stock,
                'out_of_stock': out_of_stock,
                'total_inventory_value': float(total_value),
                'last_updated': timezone.now().isoformat()
            })
        except Exception as e:
            return Response({
                'total_products': 0,
                'in_stock': 0,
                'low_stock': 0,
                'out_of_stock': 0,
                'total_inventory_value': 0,
                'error': str(e)
            }, status=status.HTTP_200_OK)
