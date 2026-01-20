from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q, Sum, F
from django.utils import timezone

from apps.purchase.models import Supplier, PurchaseOrder, PurchaseOrderItem, PurchaseReceiptLog, PaymentRecord
from apps.purchase.serializers import (
    SupplierSerializer, PurchaseOrderSerializer, PurchaseOrderItemSerializer,
    PurchaseReceiptLogSerializer, PaymentRecordSerializer, PurchaseOrderListSerializer
)
from apps.product.models import InventoryBatch, Product
from apps.auth_app.permissions import IsAuthenticated

class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for purchase endpoints."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class SupplierListCreate(ListCreateAPIView):
    """List and create suppliers."""
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['name', 'code', 'email', 'contact_person']
    ordering_fields = ['name', 'created_at', 'status']
    ordering = ['name']
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """Create supplier with permission check."""
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'manage_purchase'):
                return Response(
                    {'detail': 'Permission denied.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        supplier = serializer.save()
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class SupplierRetrieveUpdateDestroy(RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete suppliers."""
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Get supplier by ID with 404 handling."""
        return get_object_or_404(Supplier, id=self.kwargs['pk'])

    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        """Update supplier with permission check."""
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'manage_purchase'):
                return Response(
                    {'detail': 'Permission denied.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        return super().patch(request, *args, **kwargs)

class PurchaseOrderListCreate(ListCreateAPIView):
    """List and create purchase orders."""
    serializer_class = PurchaseOrderSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['supplier_id', 'status', 'payment_status']
    search_fields = ['po_number', 'supplier__name']
    ordering_fields = ['order_date', 'total_amount', 'status']
    ordering = ['-order_date']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get purchase orders with related items."""
        return PurchaseOrder.objects.prefetch_related('items').select_related('supplier')

    def get_serializer_class(self):
        """Use lightweight serializer for list view."""
        if self.request.method == 'GET':
            return PurchaseOrderListSerializer
        return PurchaseOrderSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """Create purchase order with permission check."""
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'manage_purchase'):
                return Response(
                    {'detail': 'Permission denied.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Generate PO number
        po_count = PurchaseOrder.objects.count()
        po_number = f"{timezone.now().strftime('%Y%m')}{str(po_count + 1).zfill(6)}"
        
        po = serializer.save(
            po_number=po_number,
            created_by_id=request.user.id if request.user.id else None,
            status='draft'
        )
        
        return Response(PurchaseOrderSerializer(po).data, status=status.HTTP_201_CREATED)

class PurchaseOrderRetrieveUpdate(RetrieveUpdateDestroyAPIView):
    """Retrieve and update purchase orders."""
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get purchase orders with items."""
        return PurchaseOrder.objects.prefetch_related('items').select_related('supplier')

    def get_object(self):
        """Get PO by ID with 404 handling."""
        return get_object_or_404(PurchaseOrder, id=self.kwargs['pk'])

    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        """Update PO with permission check."""
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'manage_purchase'):
                return Response(
                    {'detail': 'Permission denied.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        po = self.get_object()
        
        # Only allow updates if in draft or submitted status
        if po.status not in ['draft', 'submitted']:
            return Response(
                {'detail': f'Cannot update PO in {po.status} status.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().patch(request, *args, **kwargs)

class PurchaseOrderItemListCreate(ListCreateAPIView):
    """List and create purchase order items."""
    serializer_class = PurchaseOrderItemSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['purchase_order', 'product_id']
    search_fields = ['product__name', 'product__product_code']
    ordering_fields = ['created_at', 'quantity', 'line_total']
    ordering = ['created_at']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get items with related data."""
        return PurchaseOrderItem.objects.select_related('purchase_order', 'product')

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """Create PO item with permission check."""
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'manage_purchase'):
                return Response(
                    {'detail': 'Permission denied.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = serializer.save()
        
        # Update PO totals
        po = item.purchase_order
        items = po.items.all()
        subtotal = items.aggregate(total=Sum('line_total'))['total'] or 0
        po.subtotal = subtotal
        po.total_amount = subtotal + po.tax_amount + po.shipping_cost
        po.save()
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class PurchaseOrderItemRetrieveUpdateDestroy(RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete PO items."""
    serializer_class = PurchaseOrderItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get items with related data."""
        return PurchaseOrderItem.objects.select_related('purchase_order', 'product')

    def get_object(self):
        """Get item by ID with 404 handling."""
        return get_object_or_404(PurchaseOrderItem, id=self.kwargs['pk'])

    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        """Update PO item with permission check."""
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'manage_purchase'):
                return Response(
                    {'detail': 'Permission denied.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        item = self.get_object()
        po = item.purchase_order
        
        if po.status not in ['draft', 'submitted']:
            return Response(
                {'detail': f'Cannot update items in {po.status} status PO.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        response = super().patch(request, *args, **kwargs)
        
        # Recalculate PO totals
        items = po.items.all()
        subtotal = items.aggregate(total=Sum('line_total'))['total'] or 0
        po.subtotal = subtotal
        po.total_amount = subtotal + po.tax_amount + po.shipping_cost
        po.save()
        
        return response

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        """Delete PO item with permission check."""
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'manage_purchase'):
                return Response(
                    {'detail': 'Permission denied.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        item = self.get_object()
        po = item.purchase_order
        
        if po.status not in ['draft', 'submitted']:
            return Response(
                {'detail': f'Cannot delete items from {po.status} status PO.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        response = super().delete(request, *args, **kwargs)
        
        # Recalculate PO totals
        items = po.items.all()
        subtotal = items.aggregate(total=Sum('line_total'))['total'] or 0
        po.subtotal = subtotal
        po.total_amount = subtotal + po.tax_amount + po.shipping_cost
        po.save()
        
        return response

class PurchaseOrderApproveView(APIView):
    """Approve a purchase order."""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """Approve PO."""
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'approve_purchase'):
                return Response(
                    {'detail': 'Permission denied.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        po_id = kwargs.get('pk')
        po = get_object_or_404(PurchaseOrder, id=po_id)
        
        if po.status != 'draft':
            return Response(
                {'detail': f'Cannot approve PO in {po.status} status.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if po.items.count() == 0:
            return Response(
                {'detail': 'Cannot approve PO without items.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        po.status = 'approved'
        po.approved_by_id = request.user.id if request.user.id else None
        po.approved_at = timezone.now()
        po.save()
        
        return Response(
            PurchaseOrderSerializer(po).data,
            status=status.HTTP_200_OK
        )

class PurchaseReceiptCreateView(ListCreateAPIView):
    """List and create purchase receipts (GRN)."""
    serializer_class = PurchaseReceiptLogSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['purchase_order', 'quality_status']
    ordering_fields = ['receipt_date']
    ordering = ['-receipt_date']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get receipts with related data."""
        return PurchaseReceiptLog.objects.select_related('purchase_order')

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """Create receipt and generate batches."""
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'receive_stock'):
                return Response(
                    {'detail': 'Permission denied.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        po_id = request.data.get('purchase_order')
        po = get_object_or_404(PurchaseOrder, id=po_id)
        
        # Generate GRN number
        grn_count = PurchaseReceiptLog.objects.count()
        grn_number = f"{timezone.now().strftime('%Y%m')}{str(grn_count + 1).zfill(6)}"
        
        receipt = serializer.save(
            grn_number=grn_number,
            received_by_id=request.user.id if request.user.id else None
        )
        
        # Create inventory batches from receipt items
        items_data = request.data.get('items_json', {})
        if items_data:
            try:
                item = PurchaseOrderItem.objects.get(id=items_data.get('item_id'))
                batch = InventoryBatch.objects.create(
                    product=item.product,
                    batch_number=items_data.get('batch_number'),
                    supplier_id=po.supplier_id,
                    reference_purchase_id=po.id,
                    received_quantity=items_data.get('received_qty'),
                    remaining_quantity=items_data.get('received_qty'),
                    unit_cost=item.unit_price,
                    manufacture_date=request.data.get('manufacture_date'),
                    expiry_date=request.data.get('expiry_date')
                )
                
                # Update PO item received quantity
                item.received_quantity = items_data.get('received_qty')
                item.save()
                
                # Update PO status
                if po.status == 'approved':
                    po.status = 'partially_received'
                    po.save()
                
                # Check if fully received
                total_ordered = po.items.aggregate(total=Sum('quantity'))['total'] or 0
                total_received = po.items.aggregate(total=Sum('received_quantity'))['total'] or 0
                
                if total_received >= total_ordered:
                    po.status = 'received'
                    po.save()
            
            except PurchaseOrderItem.DoesNotExist:
                return Response(
                    {'detail': 'Item not found in this PO.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(
            PurchaseReceiptLogSerializer(receipt).data,
            status=status.HTTP_201_CREATED
        )

class PaymentRecordListCreate(ListCreateAPIView):
    """List and create payment records."""
    serializer_class = PaymentRecordSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['purchase_order', 'payment_method']
    ordering_fields = ['payment_date']
    ordering = ['-payment_date']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get payments with related data."""
        return PaymentRecord.objects.select_related('purchase_order')

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """Record payment with permission check."""
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'manage_purchase'):
                return Response(
                    {'detail': 'Permission denied.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        po_id = request.data.get('purchase_order')
        po = get_object_or_404(PurchaseOrder, id=po_id)
        
        amount = request.data.get('amount')
        
        # Update PO payment tracking
        po.paid_amount += amount
        
        # Determine payment status
        if po.paid_amount >= po.total_amount:
            po.payment_status = 'paid'
        elif po.paid_amount > 0:
            po.payment_status = 'partial'
        
        po.save()
        
        payment = serializer.save(
            recorded_by_id=request.user.id if request.user.id else None
        )
        

class DirectStockInwardView(APIView):
    """
    Simplified Stock Inward:
    1. Create Purchase Order (Received)
    2. Create Items
    3. Create GRN (Receipt) -> Triggers Batch Creation
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        # 1. Permission Check
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'manage_inventory') and not has_permission(request.user, 'manage_purchase'):
                return Response(
                    {'detail': 'Permission denied.'},
                    status=status.HTTP_403_FORBIDDEN
                )

        # 2. Extract Data
        data = request.data
        supplier_id = data.get('supplier_id')
        invoice_number = data.get('invoice_number')
        items = data.get('items', []) # List of {product_id, quantity, purchasePrice, sellingPrice}

        if not supplier_id or not items:
             return Response({'detail': 'Supplier and Items are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Create Purchase Order
        po_count = PurchaseOrder.objects.count()
        po_number = f"DIR-{timezone.now().strftime('%Y%m')}{str(po_count + 1).zfill(6)}"
        
        po = PurchaseOrder.objects.create(
            po_number=po_number,
            supplier_id=supplier_id,
            status='received', # Auto-received
            payment_status='pending',
            created_by_id=request.user.id if request.user.id else None,
            approved_by_id=request.user.id if request.user.id else None, # Auto-approve
            approved_at=timezone.now(),
            notes=f"Direct Stock Inward. Invoice: {invoice_number}"
        )

        total_amount = 0
        
        # 4. Process Items & Create Batches
        for item_data in items:
            product_id = item_data.get('product_id')
            qty = int(item_data.get('quantity') or 0)
            cost = float(item_data.get('purchasePrice') or 0)
            # selling_price = float(item_data.get('sellingPrice') or 0) # Update product price? Maybe optional.
            
            if qty <= 0: continue

            # Create PO Item
            po_item = PurchaseOrderItem.objects.create(
                purchase_order=po,
                product_id=product_id,
                quantity=qty,
                unit_price=cost,
                line_total=qty * cost,
                received_quantity=qty # Fully received
            )
            total_amount += (qty * cost)

            # Create Batch
            # Check for existing open batch for this product/price? Or always create new?
            # User requirement: "Stock Inward = Purchase Entry".
            # We create a new batch for tracking.
            batch_number = f"BAT-{po.po_number}-{product_id}"
            
            InventoryBatch.objects.create(
                product_id=product_id,
                batch_number=batch_number,
                supplier_id=supplier_id,
                reference_purchase_id=po.id,
                received_quantity=qty,
                remaining_quantity=qty,
                unit_cost=cost,
                manufacture_date=None, # Optional
                expiry_date=None # Optional
            )

            # Update Product Stock (denormalized field on Product model)
            # logic in InventoryPage suggests it sums batches, but Product model has `stock` field.
            # We should update it.
            Product.objects.filter(id=product_id).update(stock=F('stock') + qty)

        # 5. Update PO Totals
        po.total_amount = total_amount
        po.subtotal = total_amount
        po.save()

        # 6. Create Receipt Log (GRN) for record
        grn_count = PurchaseReceiptLog.objects.count()
        grn_number = f"GRN-{timezone.now().strftime('%Y%m')}{str(grn_count + 1).zfill(6)}"
        
        PurchaseReceiptLog.objects.create(
            grn_number=grn_number,
            purchase_order=po,
            invoice_number=invoice_number,
            received_by_id=request.user.id if request.user.id else None,
            items_json=items, # Store raw items data for reference
            notes="Auto-generated via Direct Stock Inward"
        )

        return Response({'message': 'Stock Inward Successful', 'po_number': po.po_number}, status=status.HTTP_201_CREATED)

