from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.pagination import PageNumberPagination
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Q
from decimal import Decimal
from .models import Invoice, InvoiceItem, InvoiceReturn
from .serializers import InvoiceSerializer, InvoiceReturnSerializer
from apps.auth_app.permissions import IsAuthenticated
from apps.super_admin.models import SystemSettings
import uuid

class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

from apps.common.models import CompanyProfile
from apps.common.serializers import CompanyProfileSerializer

def generate_invoice_number(company_code="GEO", inv_prefix="INV", starting_number=1001):
    """
    Generate unique invoice number with format: {COMPANY_CODE}-{INV_PREFIX}-{SEQUENCE}
    Example: ABC-INV-1001, ABC-INV-1002, ABC1-BILL-1001, etc.
    """
    # Find the latest invoice number for this company code
    latest_invoice = Invoice.objects.filter(
        invoice_number__startswith=f"{company_code}-"
    ).order_by('-created_at').first()
    
    if latest_invoice:
        # Extract the sequence number and increment
        try:
            # Format: ABC-INV-1001, ABC-INV-1002, etc.
            parts = latest_invoice.invoice_number.split('-')
            if len(parts) >= 3:
                last_seq = int(parts[-1])
                next_seq = last_seq + 1
            else:
                next_seq = starting_number
        except (ValueError, IndexError):
            next_seq = starting_number
    else:
        next_seq = starting_number
    
    return f"{company_code}-{inv_prefix}-{next_seq}"

class InvoiceListCreateView(ListCreateAPIView):
    """List and create invoices."""
    queryset = Invoice.objects.prefetch_related('items', 'customer')
    serializer_class = InvoiceSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Invoice.objects.prefetch_related('items', 'customer')
        
        # Filter by owner (User can only see their company's invoices)
        user = self.request.user
        if user.parent: # Sales Exec
             owner = user.parent
        else: # Owner or Super Admin
             owner = user
        
        # If Super Admin, they might want to see all, but let's default to restricting or filtering by owner_id param
        # For now, let's assume we filter by the effective owner field we just added
        # But wait, we haven't migrated existing data so owner might be null for old rows.
        # Let's keep existing filters and just add owner filter if 'owner_id' passed, or restrict normal users
        
        if not user.is_super_admin:
             # Restrict to invoices owned by this company
             from apps.common.helpers import get_user_owner
             owner = get_user_owner(user)
             if owner:
                 queryset = queryset.filter(owner=owner)

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by payment status
        payment_status = self.request.query_params.get('payment_status')
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)
        
        # Filter by customer
        customer_id = self.request.query_params.get('customer_id')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        
        # Date range filter
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(invoice_date__date__range=[start_date, end_date])
        
        return queryset.order_by('-invoice_date')

    @transaction.atomic
    def perform_create(self, serializer):
        # Permission check
        if not self.request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(self.request.user, 'manage_invoices'):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("You do not have permission to manage invoices.")

        try:
            user = self.request.user
            
            # 1. Resolve Effective Owner (Seller)
            if user.parent:
                owner = user.parent
            else:
                owner = user
                
            # 2. Fetch Company Profile
            try:
                company_profile = CompanyProfile.objects.get(owner=owner)
                # Snapshot company details
                company_snapshot = CompanyProfileSerializer(company_profile).data
                
                # Get or generate company code
                company_code = company_profile.company_code
                if not company_code:
                    # Auto-generate company code from first 3 letters of company name
                    base_code = company_profile.company_name[:3].upper()
                    company_code = ''.join(e for e in base_code if e.isalnum()).upper()
                    
                    # Check for duplicates and add incremental number
                    existing_count = CompanyProfile.objects.filter(
                        company_code__startswith=company_code
                    ).count()
                    if existing_count > 0:
                        company_code = f"{company_code}{existing_count}"
                    
                    # Save the generated code
                    company_profile.company_code = company_code
                    company_profile.save(update_fields=['company_code'])
                
                billing_settings = company_profile.billing_settings
                
            except CompanyProfile.DoesNotExist:
                # Fallback if no profile exists
                company_snapshot = {}
                company_code = "INV"
                company_profile = None
                billing_settings = {}

            # 3. Get INV Prefix and Starting Number from SystemSettings
            inv_prefix = "INV"
            starting_number = 1001
            try:
                system_settings = SystemSettings.objects.first()
                if system_settings:
                    if system_settings.invoice_prefix:
                        inv_prefix = system_settings.invoice_prefix
                    if system_settings.invoice_starting_number:
                        starting_number = system_settings.invoice_starting_number
            except SystemSettings.DoesNotExist:
                pass

            # 4. Generate Invoice Number with company code and INV prefix
            invoice_number = generate_invoice_number(company_code, inv_prefix, starting_number)
            
            # 5. Create Invoice Instance
            invoice = serializer.save(
                invoice_number=invoice_number,
                created_by_id=user.id,
                owner=owner,
                company_details=company_snapshot,
                paid_amount=0 
            )
            
            # Determine billing mode from request
            if 'billing_mode' in self.request.data:
                 invoice.billing_mode = self.request.data['billing_mode']
            
            # Set tax rate if provided (default 18% for GST)
            if 'tax_rate' in self.request.data:
                invoice.tax_rate = Decimal(str(self.request.data['tax_rate']))
            else:
                invoice.tax_rate = Decimal('18')  # Default tax rate for GST

            # 5. Process items
            items_data = self.request.data.get('items', [])
            for item in items_data:
                # Handle product ID safely
                product_id = item.get('id')
                valid_product_id = None
                if isinstance(product_id, int) or (isinstance(product_id, str) and product_id.isdigit()):
                    valid_product_id = int(product_id)

                # Map frontend 'qty' 'price' to backend fields
                invoice_item = InvoiceItem.objects.create(
                    invoice=invoice,
                    product_id=valid_product_id,
                    product_name=item.get('name', 'Unknown Product'),
                    product_code=item.get('sku', ''),
                    quantity=int(item.get('qty', 1)),
                    unit_price=Decimal(str(item.get('price', 0))),
                    tax_rate=Decimal(str(item.get('tax', 0))),
                    discount_percent=0 
                )
                
                # 6. Tax Logic (IGST vs CGST/SGST)
                # We calculate this at item level but currently model supports line_total.
                # The Invoice model has calculating logic, let's override/update it later or rely on invoice.calculate_tax()
                
                invoice_item.calculate_line_total()
                invoice_item.save()

                # Deduct Stock
                if valid_product_id:
                    try:
                        from apps.product.models import Product
                        product = Product.objects.get(id=valid_product_id)
                        product.deduct_stock(
                            quantity=invoice_item.quantity,
                            reference_id=invoice.id,
                            reference_type='invoice',
                            user=user
                        )
                    except Product.DoesNotExist:
                        pass

            # Recalculate invoice subtotal from items
            invoice.subtotal = invoice.items.aggregate(total=Sum('line_total'))['total'] or Decimal('0')
            
            # 7. Apply Tax Logic based on State
            # Verify if Customer state matches Company state
            customer_state = None
            if invoice.customer:
                # Try to get state from addresses: Billing > Default > Any
                address = invoice.customer.addresses.filter(type='billing').first() or \
                          invoice.customer.addresses.filter(is_default=True).first() or \
                          invoice.customer.addresses.first()
                if address:
                    customer_state = address.state

            company_state = (company_snapshot.get('state') or '').lower() if company_snapshot else ''
            
            # Logic: If states are different -> IGST. If same -> CGST + SGST.
            # Only if tax is enabled (with_gst)
            
            if invoice.billing_mode == 'with_gst':
                tax_rate_decimal = Decimal(str(invoice.tax_rate))
                tax_amount = invoice.subtotal * (tax_rate_decimal / Decimal('100'))
                
                if customer_state and company_state and customer_state.lower() != company_state:
                     # Interstate -> IGST
                     invoice.igst_amount = tax_amount
                     invoice.cgst_amount = Decimal('0')
                     invoice.sgst_amount = Decimal('0')
                else:
                     # Intrastate (or fallback) -> CGST + SGST
                     invoice.cgst_amount = tax_amount / 2
                     invoice.sgst_amount = tax_amount / 2
                     invoice.igst_amount = Decimal('0')
                     
                invoice.total_amount = invoice.subtotal - invoice.discount_amount + invoice.igst_amount + invoice.cgst_amount + invoice.sgst_amount
            else:
                 invoice.calculate_total() # Default logic (zeros out taxes)
            
            # Apply round-off if enabled in billing settings
            if billing_settings.get('invoice_round_off', False):
                # Round to nearest rupee
                invoice.total_amount = Decimal(str(round(float(invoice.total_amount))))
            
            # Now set the paid amount
            requested_payment_status = self.request.data.get('payment_status', 'unpaid')
            if requested_payment_status == 'paid':
                invoice.paid_amount = invoice.total_amount
                invoice.payment_status = 'paid'
            elif 'paid_amount' in self.request.data:
                invoice.paid_amount = Decimal(str(self.request.data['paid_amount']))
                invoice.payment_status = requested_payment_status
            
            invoice.save()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error creating invoice: {str(e)}", exc_info=True)
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"detail": f"Backend Error: {str(e)}"})

class NextInvoiceNumberView(APIView):
    """Get the next invoice number for display."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # 1. Resolve Effective Owner (Seller)
        from apps.common.helpers import get_user_owner
        owner = get_user_owner(user)
        
        # If user is super admin and no owner context (impossible in practice for this flow?), handle gracefully
        if not owner and not user.is_super_admin:
             owner = user
            
        # 2. Get Company Code
        company_code = "INV"
        try:
            company_profile = CompanyProfile.objects.get(owner=owner)
            if company_profile.company_code:
                company_code = company_profile.company_code
            else:
                # Generate on the fly if missing (mirroring create logic)
                base_code = company_profile.company_name[:3].upper()
                company_code = ''.join(e for e in base_code if e.isalnum()).upper()
        except CompanyProfile.DoesNotExist:
            pass

        # 3. Get INV Prefix and Starting Number from SystemSettings
        inv_prefix = "INV"
        starting_number = 1001
        try:
            system_settings = SystemSettings.objects.first()
            if system_settings:
                if system_settings.invoice_prefix:
                    inv_prefix = system_settings.invoice_prefix
                if system_settings.invoice_starting_number:
                    starting_number = system_settings.invoice_starting_number
        except SystemSettings.DoesNotExist:
            pass

        # 4. Generate Number (Dry Run)
        next_number = generate_invoice_number(company_code, inv_prefix, starting_number)
        
        return Response({'next_invoice_number': next_number})

class InvoiceDetailView(RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete an invoice."""
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Invoice.objects.prefetch_related('items', 'customer')
        user = self.request.user
        if not user.is_super_admin:
            from apps.common.helpers import get_user_owner
            owner = get_user_owner(user)
            if owner:
                queryset = queryset.filter(owner=owner)
        return queryset

    def perform_update(self, serializer):
        if not self.request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(self.request.user, 'manage_invoices'):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("You do not have permission to manage invoices.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(self.request.user, 'manage_invoices'):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("You do not have permission to manage invoices.")
        instance.delete()

class InvoiceAddItemView(APIView):
    """Add items to an invoice."""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, invoice_id):
        """Add item to invoice."""
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'manage_invoices'):
                 from rest_framework.exceptions import PermissionDenied
                 raise PermissionDenied("You do not have permission to manage invoices.")

        try:
            user = request.user
            if user.is_super_admin:
                invoice = Invoice.objects.get(id=invoice_id, status='draft')
            else:
                from apps.common.helpers import get_user_owner
                owner = get_user_owner(user)
                invoice = Invoice.objects.get(id=invoice_id, status='draft', owner=owner)
        except Invoice.DoesNotExist:
            return Response({'detail': 'Invoice not found or not in draft status'}, status=status.HTTP_404_NOT_FOUND)
        
        items_data = request.data.get('items', [])
        created_items = []
        
        for item_data in items_data:
            item = InvoiceItem.objects.create(invoice=invoice, **item_data)
            item.calculate_line_total()
            item.save()
            created_items.append(item)
        
        # Recalculate invoice totals
        invoice.subtotal = invoice.items.aggregate(total=Sum('line_total'))['total'] or Decimal('0')
        invoice.calculate_total()
        invoice.save()
        
        return Response({'message': f'{len(created_items)} items added'}, status=status.HTTP_201_CREATED)

class InvoiceCompleteView(APIView):
    """Complete/finalize an invoice."""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, invoice_id):
        """Complete invoice and change status."""
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'manage_invoices'):
                 from rest_framework.exceptions import PermissionDenied
                 raise PermissionDenied("You do not have permission to manage invoices.")

        try:
            user = request.user
            if user.is_super_admin:
                invoice = Invoice.objects.get(id=invoice_id)
            else:
                from apps.common.helpers import get_user_owner
                owner = get_user_owner(user)
                invoice = Invoice.objects.get(id=invoice_id, owner=owner)
        except Invoice.DoesNotExist:
            return Response({'detail': 'Invoice not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if invoice.status == 'cancelled':
            return Response({'detail': 'Cannot complete a cancelled invoice'}, status=status.HTTP_400_BAD_REQUEST)
        
        invoice.complete()
        serializer = InvoiceSerializer(invoice)
        return Response(serializer.data)

class InvoiceCancelView(APIView):
    """Cancel an invoice."""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, invoice_id):
        """Cancel invoice."""
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'manage_invoices'):
                 from rest_framework.exceptions import PermissionDenied
                 raise PermissionDenied("You do not have permission to manage invoices.")

        try:
            user = request.user
            if user.is_super_admin:
                invoice = Invoice.objects.get(id=invoice_id)
            else:
                from apps.common.helpers import get_user_owner
                owner = get_user_owner(user)
                invoice = Invoice.objects.get(id=invoice_id, owner=owner)
        except Invoice.DoesNotExist:
            return Response({'detail': 'Invoice not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if invoice.status in ['cancelled', 'returned']:
            return Response({'detail': f'Cannot cancel a {invoice.status} invoice'}, status=status.HTTP_400_BAD_REQUEST)
        
        invoice.cancel()
        serializer = InvoiceSerializer(invoice)
        return Response(serializer.data)

class InvoiceReturnView(APIView):
    """Create or list invoice returns."""
    permission_classes = [IsAuthenticated]

    def get(self, request, invoice_id):
        """Get returns for an invoice."""
        try:
            user = request.user
            if user.is_super_admin:
                invoice = Invoice.objects.get(id=invoice_id)
            else:
                from apps.common.helpers import get_user_owner
                owner = get_user_owner(user)
                invoice = Invoice.objects.get(id=invoice_id, owner=owner)
            returns = InvoiceReturn.objects.filter(invoice=invoice)
            serializer = InvoiceReturnSerializer(returns, many=True)
            return Response(serializer.data)
        except Invoice.DoesNotExist:
            return Response({'detail': 'Invoice not found'}, status=status.HTTP_404_NOT_FOUND)

    @transaction.atomic
    def post(self, request, invoice_id):
        """Create return for invoice."""
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'manage_invoices'):
                 from rest_framework.exceptions import PermissionDenied
                 raise PermissionDenied("You do not have permission to manage invoices.")

        try:
            user = request.user
            if user.is_super_admin:
                invoice = Invoice.objects.get(id=invoice_id)
            else:
                from apps.common.helpers import get_user_owner
                owner = get_user_owner(user)
                invoice = Invoice.objects.get(id=invoice_id, owner=owner)
        except Invoice.DoesNotExist:
            return Response({'detail': 'Invoice not found'}, status=status.HTTP_404_NOT_FOUND)
        
        return_number = f"RET-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
        
        invoice_return = InvoiceReturn.objects.create(
            return_number=return_number,
            invoice=invoice,
            reason=request.data.get('reason'),
            returned_items=request.data.get('returned_items', []),
            return_amount=request.data.get('return_amount', 0),
            refund_amount=request.data.get('refund_amount', 0),
            created_by_id=request.user.id if hasattr(request, 'user') else None
        )
        
        serializer = InvoiceReturnSerializer(invoice_return)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

from rest_framework import viewsets
from .models import DiscountRule, DiscountLog
from .serializers import DiscountRuleSerializer, DiscountLogSerializer

class DiscountRuleViewSet(viewsets.ModelViewSet):
    """CRUD for Discount Rules."""
    queryset = DiscountRule.objects.all()
    serializer_class = DiscountRuleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = DiscountRule.objects.all()
        if not user.is_super_admin:
            from apps.common.helpers import get_user_owner
            owner = get_user_owner(user)
            if owner:
                queryset = queryset.filter(owner=owner)
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        from apps.common.helpers import get_user_owner
        owner = get_user_owner(self.request.user)
        serializer.save(created_by=self.request.user, owner=owner)

class DiscountLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only view for Discount Logs."""
    queryset = DiscountLog.objects.all()
    serializer_class = DiscountLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = DiscountLog.objects.all()
        if not user.is_super_admin:
            from apps.common.helpers import get_user_owner
            owner = get_user_owner(user)
            if owner:
                queryset = queryset.filter(invoice__owner=owner)
        return queryset.order_by('-timestamp')
