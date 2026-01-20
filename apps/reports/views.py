from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Count, F, Q, DecimalField
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from apps.auth_app.permissions import IsAuthenticated
from apps.billing.models import Invoice, InvoiceItem
from apps.product.models import Product, InventoryBatch
from apps.customer.models import Customer
from apps.purchase.models import PurchaseOrder, PurchaseOrderItem
from decimal import Decimal
import csv
from django.http import HttpResponse

class SalesReportView(APIView):
    """Sales report."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get sales report with filtering."""
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'view_reports'):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("You do not have permission to view reports.")

        period = request.query_params.get('period', 'month')  # day, week, month, year, all
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        from apps.common.helpers import get_user_owner
        owner = get_user_owner(request.user)
        
        query = Invoice.objects.filter(status='completed')
        if owner:
            query = query.filter(owner=owner)
        
        # Apply period filter
        if period == 'day':
            query = query.filter(invoice_date__date=timezone.now().date())
        elif period == 'week':
            start = timezone.now().date() - timedelta(days=7)
            query = query.filter(invoice_date__date__gte=start)
        elif period == 'month':
            start = timezone.now().date().replace(day=1)
            query = query.filter(invoice_date__date__gte=start)
        elif period == 'year':
            start = timezone.now().date().replace(month=1, day=1)
            query = query.filter(invoice_date__date__gte=start)
        
        if start_date and end_date:
            query = query.filter(invoice_date__date__range=[start_date, end_date])
        
        # Aggregate data results may be None if no records found
        agg_result = query.aggregate(
            total_invoices=Count('id'),
            total_amount=Sum('total_amount'),
            total_discount=Sum('discount_amount'),
            total_tax=Sum('cgst_amount') + Sum('sgst_amount') + Sum('igst_amount'),
            cash_received=Sum('paid_amount')
        )
        
        # Safely handle None values
        total_sales = agg_result['total_amount'] or 0
        cash_received = agg_result['cash_received'] or 0
        
        aggregates = {
            'total_invoices': agg_result['total_invoices'] or 0,
            'total_amount': total_sales,
            'total_discount': agg_result['total_discount'] or 0,
            'total_tax': agg_result['total_tax'] or 0,
            'cash_received': cash_received,
            'pending_amount': total_sales - cash_received
        }
        
        # Get top products
        item_query = InvoiceItem.objects.filter(
            invoice__status='completed'
        )
        if owner:
            item_query = item_query.filter(invoice__owner=owner)
            
        top_products = item_query.values('product_name').annotate(
            qty=Sum('quantity'),
            total=Sum('line_total')
        ).order_by('-qty')[:10]
        
        return Response({
            'period': period,
            'aggregates': aggregates,
            'top_products': list(top_products)
        })

class InventoryReportView(APIView):
    """Inventory report."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get inventory report."""
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'view_reports'):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("You do not have permission to view reports.")

        from apps.common.helpers import get_user_owner
        owner = get_user_owner(request.user)
        
        # Low stock items
        product_qs = Product.objects.all()
        if owner:
            product_qs = product_qs.filter(owner=owner)
            
        low_stock = product_qs.filter(stock__lte=F('reorder_level')).values(
            'id', 'name', 'product_code', 'stock', 'reorder_level'
        ).order_by('stock')
        
        # Total inventory value
        batch_qs = InventoryBatch.objects.all()
        if owner:
            batch_qs = batch_qs.filter(product__owner=owner)
            
        batches = batch_qs.aggregate(
            total_batches=Count('id'),
            total_quantity=Sum('remaining_quantity'),
            total_value=Sum(F('remaining_quantity') * F('purchase_price'), output_field=DecimalField())
        )
        
        # Out of stock
        out_of_stock = product_qs.filter(stock=0).count()
        
        return Response({
            'low_stock_items': list(low_stock),
            'batches': batches,
            'out_of_stock_count': out_of_stock,
            'total_products': product_qs.count()
        })

class TaxReportView(APIView):
    """GST/Tax report."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get tax report."""
        if not request.user.is_superuser:
             from apps.users.utils import has_permission
             if not has_permission(request.user, 'view_reports'):
                 from rest_framework.exceptions import PermissionDenied
                 raise PermissionDenied("You do not have permission to view reports.")

        period = request.query_params.get('period', 'month')
        
        from apps.common.helpers import get_user_owner
        owner = get_user_owner(request.user)
        
        query = Invoice.objects.filter(status='completed')
        if owner:
            query = query.filter(owner=owner)
        
        if period == 'month':
            start = timezone.now().date().replace(day=1)
            query = query.filter(invoice_date__date__gte=start)
        elif period == 'quarter':
            month = timezone.now().month
            quarter_start = ((month - 1) // 3) * 3 + 1
            start = timezone.now().date().replace(month=quarter_start, day=1)
            query = query.filter(invoice_date__date__gte=start)
        elif period == 'year':
            start = timezone.now().date().replace(month=1, day=1)
            query = query.filter(invoice_date__date__gte=start)
        
        aggregates = query.aggregate(
            total_cgst=Sum('cgst_amount'),
            total_sgst=Sum('sgst_amount'),
            total_igst=Sum('igst_amount'),
            total_tax=Sum('cgst_amount') + Sum('sgst_amount') + Sum('igst_amount'),
            total_sales=Sum('total_amount')
        )
        
        return Response({
            'period': period,
            'tax_data': aggregates
        })

class ProfitLossReportView(APIView):
    """Profit & Loss report."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get P&L report."""
        if not request.user.is_superuser:
             from apps.users.utils import has_permission
             if not has_permission(request.user, 'view_reports'):
                 from rest_framework.exceptions import PermissionDenied
                 raise PermissionDenied("You do not have permission to view reports.")

        period = request.query_params.get('period', 'month')
        
        from apps.common.helpers import get_user_owner
        owner = get_user_owner(request.user)
        
        # Sales
        sales_query = Invoice.objects.filter(status='completed')
        purchase_query = PurchaseOrder.objects.filter(status='received')
        
        if owner:
            sales_query = sales_query.filter(owner=owner)
            purchase_query = purchase_query.filter(owner=owner)
        
        if period == 'month':
            start = timezone.now().date().replace(day=1)
            sales_query = sales_query.filter(invoice_date__date__gte=start)
            purchase_query = purchase_query.filter(order_date__date__gte=start)
        
        sales = sales_query.aggregate(total=Sum('total_amount'))['total'] or 0
        discount = sales_query.aggregate(total=Sum('discount_amount'))['total'] or 0
        tax = sales_query.aggregate(
            total=Sum('cgst_amount') + Sum('sgst_amount') + Sum('igst_amount')
        )['total'] or 0
        
        # Cost
        item_query = PurchaseOrderItem.objects.filter(
            purchase_order__status='received'
        )
        if owner:
            item_query = item_query.filter(purchase_order__owner=owner)
            
        cost_of_goods = item_query.aggregate(
            total=Sum(F('quantity') * F('unit_price'), output_field=DecimalField())
        )['total'] or 0
        
        profit = (sales - discount) - cost_of_goods
        
        return Response({
            'period': period,
            'sales': float(sales),
            'discount': float(discount),
            'tax': float(tax),
            'cost_of_goods': float(cost_of_goods),
            'profit': float(profit),
            'profit_margin': float((profit / sales * 100) if sales > 0 else 0)
        })

class ExportReportView(APIView):
    """Export report to CSV."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Export report."""
        if not request.user.is_superuser:
             from apps.users.utils import has_permission
             if not has_permission(request.user, 'export_reports'):
                 from rest_framework.exceptions import PermissionDenied
                 raise PermissionDenied("You do not have permission to export reports.")

        report_type = request.query_params.get('type', 'sales')
        
        if report_type == 'sales':
            return self._export_sales()
        elif report_type == 'inventory':
            return self._export_inventory()
        elif report_type == 'tax':
            return self._export_tax()
        else:
            return Response({'detail': 'Invalid report type'}, status=status.HTTP_400_BAD_REQUEST)

    def _export_sales(self):
        """Export sales data to CSV."""
        from apps.common.helpers import get_user_owner
        owner = get_user_owner(request.user)
        
        invoices = Invoice.objects.filter(status='completed')
        if owner:
            invoices = invoices.filter(owner=owner)
            
        invoices = invoices.values(
            'invoice_number', 'customer__name', 'total_amount', 'paid_amount', 'invoice_date'
        )
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sales_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Invoice Number', 'Customer', 'Total Amount', 'Paid Amount', 'Date'])
        for row in invoices:
            writer.writerow([row['invoice_number'], row['customer__name'], row['total_amount'], row['paid_amount'], row['invoice_date']])
        
        return response

    def _export_inventory(self):
        """Export inventory data to CSV."""
        from apps.common.helpers import get_user_owner
        owner = get_user_owner(request.user)
        
        products = Product.objects.all()
        if owner:
            products = products.filter(owner=owner)
            
        products = products.values('product_code', 'name', 'stock', 'reorder_level')
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="inventory_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Product Code', 'Name', 'Stock', 'Reorder Level'])
        for row in products:
            writer.writerow([row['product_code'], row['name'], row['stock'], row['reorder_level']])
        
        return response

    def _export_tax(self):
        """Export tax data to CSV."""
        from apps.common.helpers import get_user_owner
        owner = get_user_owner(request.user)
        
        invoices = Invoice.objects.filter(status='completed')
        if owner:
            invoices = invoices.filter(owner=owner)
            
        invoices = invoices.values(
            'invoice_number', 'cgst_amount', 'sgst_amount', 'igst_amount', 'invoice_date'
        )
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="tax_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Invoice Number', 'CGST', 'SGST', 'IGST', 'Date'])
        for row in invoices:
            writer.writerow([row['invoice_number'], row['cgst_amount'], row['sgst_amount'], row['igst_amount'], row['invoice_date']])
        
        return response
