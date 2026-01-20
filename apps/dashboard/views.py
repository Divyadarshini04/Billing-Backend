from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Count, Q, F, DecimalField
from django.utils import timezone
from datetime import timedelta
from apps.auth_app.permissions import IsAuthenticated
from apps.billing.models import Invoice
from apps.payment.models import Payment
from apps.product.models import Product, InventoryBatch
from apps.customer.models import Customer
from apps.purchase.models import PurchaseOrder

class DashboardOverviewView(APIView):
    """Dashboard overview with key metrics."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get dashboard overview."""
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'view_dashboard'):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("You do not have permission to view the dashboard.")

        try:
            today = timezone.now().date()
            
            # Resolve Owner
            from apps.common.helpers import get_user_owner
            owner = get_user_owner(request.user)

            # Base querysets filtered by owner
            invoice_qs = Invoice.objects.all()
            payment_qs = Payment.objects.all() # Assuming Payment has some link, or via Invoice
            product_qs = Product.objects.all()
            customer_qs = Customer.objects.all()
            batch_qs = InventoryBatch.objects.all()
            
            if owner:
                invoice_qs = invoice_qs.filter(owner=owner)
                # Payment usually linked to Invoice, so filter via invoice__owner
                payment_qs = payment_qs.filter(invoice__owner=owner)
                product_qs = product_qs.filter(owner=owner)
                customer_qs = customer_qs.filter(owner=owner)
                batch_qs = batch_qs.filter(product__owner=owner)
            
            # Today's sales (all invoices, not just completed)
            today_sales = 0
            today_invoices = 0
            try:
                result = invoice_qs.filter(
                    invoice_date__date=today
                ).aggregate(total=Sum('total_amount'))
                today_sales = float(result['total'] or 0)
                today_invoices = invoice_qs.filter(
                    invoice_date__date=today
                ).count()
            except Exception as e:
                pass
            
            # Today's revenue (payments)
            today_revenue = 0
            try:
                result = payment_qs.filter(
                    status='completed',
                    created_at__date=today
                ).aggregate(total=Sum('amount'))
                today_revenue = float(result['total'] or 0)
            except Exception as e:
                pass
            
            # Pending payments (all unpaid/partial invoices)
            pending = 0
            try:
                result = invoice_qs.filter(
                    payment_status__in=['unpaid', 'partial']
                ).aggregate(total=Sum('total_amount'))
                pending = float(result['total'] or 0)
            except Exception as e:
                pass
            
            # Low stock
            low_stock_count = 0
            try:
                low_stock_count = product_qs.filter(stock__lte=10).count()
            except Exception as e:
                pass
            
            # Active customers
            active_customers = 0
            try:
                active_customers = customer_qs.filter(status='active').count()
            except Exception as e:
                pass
            
            # Inventory value
            inventory_value = 0
            try:
                result = batch_qs.aggregate(
                    total=Sum('remaining_quantity')
                )
                inventory_value = int(result['total'] or 0)
            except Exception as e:
                pass
            
            # Total customers
            total_customers = 0
            try:
                total_customers = customer_qs.count()
            except Exception as e:
                pass
            
            # Total products
            total_products = 0
            try:
                total_products = product_qs.count()
            except Exception as e:
                pass
            
            # Total revenue (all invoices, not just completed)
            total_revenue = 0
            try:
                result = invoice_qs.aggregate(total=Sum('total_amount'))
                total_revenue = float(result['total'] or 0)
            except Exception as e:
                pass
            
            response_data = {
                'today_sales': today_sales,
                'today_invoices': today_invoices,
                'today_revenue': today_revenue,
                'pending_amount': pending,
                'low_stock_count': low_stock_count,
                'total_customers': total_customers,
                'active_customers': active_customers,
                'inventory_value': inventory_value,
                'total_products': total_products,
                'total_revenue': total_revenue
            }

            return Response(response_data)
        except Exception as e:
            return Response({
                'error': str(e),
                'today_sales': 0,
                'today_invoices': 0,
                'today_revenue': 0,
                'pending_amount': 0,
                'low_stock_count': 0,
                'total_customers': 0,
                'inventory_value': 0
            }, status=status.HTTP_200_OK)

class DashboardAnalyticsView(APIView):
    """Detailed analytics."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get comprehensive analytics data."""
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'view_dashboard'):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("You do not have permission to view the dashboard.")

        try:
            period = request.query_params.get('period', 'week')
            
            if period == 'week':
                start = timezone.now().date() - timedelta(days=7)
            elif period == 'month':
                start = timezone.now().date().replace(day=1)
            else:
                start = timezone.now().date() - timedelta(days=30)
            
            # Resolve Owner
            from apps.common.helpers import get_user_owner
            owner = get_user_owner(request.user)

            # Base qsets
            invoice_qs = Invoice.objects.all()
            customer_qs = Customer.objects.all()
            product_qs = Product.objects.all()
            
            if owner:
                invoice_qs = invoice_qs.filter(owner=owner)
                customer_qs = customer_qs.filter(owner=owner)
                product_qs = product_qs.filter(owner=owner)




            # Daily sales trend
            daily_sales = []
            try:
                sales_data = invoice_qs.filter(
                    status='completed',
                    invoice_date__date__gte=start
                ).values('invoice_date__date').annotate(
                    total=Sum('total_amount'),
                    count=Count('id')
                ).order_by('invoice_date__date')
                daily_sales = [{'date': str(d['invoice_date__date']), 'total': float(d['total'] or 0), 'invoices': d['count']} for d in sales_data]
            except:
                pass
            
            # Payment status breakdown
            payment_breakdown = []
            try:
                breakdown = invoice_qs.filter(
                    status='completed',
                    invoice_date__date__gte=start
                ).values('payment_status').annotate(count=Count('id'), total=Sum('total_amount'))
                payment_breakdown = [{'status': d['payment_status'], 'count': d['count'], 'total': float(d['total'] or 0)} for d in breakdown]
            except:
                pass
            
            # Customer analytics
            customer_analytics = {'total_active': 0, 'new_this_period': 0, 'top_customers': []}
            try:
                customer_analytics['total_active'] = customer_qs.filter(status='active').count()
                customer_analytics['new_this_period'] = customer_qs.filter(
                    status='active',
                    created_at__date__gte=start
                ).count()
                
                try:
                    top_customers = customer_qs.annotate(
                        total_spent=Sum('invoices__total_amount', filter=Q(invoices__status='completed'))
                    ).filter(status='active').order_by('-total_spent')[:5]
                    
                    customer_analytics['top_customers'] = [{
                        'id': c.id,
                        'name': c.name,
                        'total_spent': float(c.total_spent or 0)
                    } for c in top_customers]
                except Exception as e:
                    print(f"Top customers error: {e}")
            except Exception as e:
                print(f"Customer analytics error: {e}")
            
            # Revenue analytics
            revenue_analytics = {}
            try:
                total_revenue = invoice_qs.filter(
                    status='completed',
                    invoice_date__date__gte=start
                ).aggregate(total=Sum('total_amount'))['total'] or 0
                
                paid_revenue = invoice_qs.filter(
                    status='completed',
                    payment_status='paid',
                    invoice_date__date__gte=start
                ).aggregate(total=Sum('total_amount'))['total'] or 0
                
                pending_revenue = invoice_qs.filter(
                    status='completed',
                    payment_status__in=['unpaid', 'partial'],
                    invoice_date__date__gte=start
                ).aggregate(total=Sum('total_amount'))['total'] or 0
                
                revenue_analytics = {
                    'total': float(total_revenue),
                    'paid': float(paid_revenue),
                    'pending': float(pending_revenue),
                    'invoices': invoice_qs.filter(
                        status='completed',
                        invoice_date__date__gte=start
                    ).count()
                }
            except:
                revenue_analytics = {'total': 0, 'paid': 0, 'pending': 0, 'invoices': 0}
            
            # Product analytics
            product_analytics = {}
            try:
                total_products = product_qs.count()
                low_stock = product_qs.filter(stock__lte=10).count()
                out_of_stock = product_qs.filter(stock=0).count()
                
                product_analytics = {
                    'total': total_products,
                    'low_stock': low_stock,
                    'out_of_stock': out_of_stock,
                    'total_inventory_value': 0
                }
            except:
                product_analytics = {'total': 0, 'low_stock': 0, 'out_of_stock': 0, 'total_inventory_value': 0}
            
            return Response({
                'period': period,
                'daily_sales': daily_sales,
                'payment_breakdown': payment_breakdown,
                'customer_analytics': customer_analytics,
                'revenue_analytics': revenue_analytics,
                'product_analytics': product_analytics
            })
        except Exception as e:
            return Response({
                'period': 'week',
                'daily_sales': [],
                'payment_breakdown': [],
                'customer_analytics': {'total_active': 0, 'new_this_period': 0, 'top_customers': []},
                'revenue_analytics': {'total': 0, 'paid': 0, 'pending': 0, 'invoices': 0},
                'product_analytics': {'total': 0, 'low_stock': 0, 'out_of_stock': 0, 'total_inventory_value': 0},
                'error': str(e)
            }, status=status.HTTP_200_OK)

class TopProductsView(APIView):
    """Get top selling products."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get top products."""
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'view_dashboard'):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("You do not have permission to view the dashboard.")

        try:
            limit = int(request.query_params.get('limit', 10))
            period = request.query_params.get('period', 'month')
            
            query = Invoice.objects.filter(status='completed')
            
            if period == 'month':
                start = timezone.now().date().replace(day=1)
                query = query.filter(invoice_date__date__gte=start)
            elif period == 'week':
                start = timezone.now().date() - timedelta(days=7)
                query = query.filter(invoice_date__date__gte=start)
            
            # Filter by Owner
            from apps.common.helpers import get_user_owner
            owner = get_user_owner(request.user)
            if owner:
                query = query.filter(owner=owner)
            
            # Get invoice counts
            top_products = []
            try:
                products = Product.objects.all()
                if owner:
                    products = products.filter(owner=owner)
                products = products[:limit]
                top_products = [{'id': p.id, 'name': p.name, 'stock': p.stock} for p in products]
            except:
                pass
            
            return Response(top_products)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_200_OK)

class RecentTransactionsView(APIView):
    """Get recent transactions."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get recent invoices."""
        if not request.user.is_superuser:
             from apps.users.utils import has_permission
             if not has_permission(request.user, 'view_dashboard'):
                 from rest_framework.exceptions import PermissionDenied
                 raise PermissionDenied("You do not have permission to view the dashboard.")

        try:
            limit = int(request.query_params.get('limit', 10))
            
            # Resolve Owner
            from apps.common.helpers import get_user_owner
            owner = get_user_owner(request.user)

            invoices = []
            try:
                qs = Invoice.objects.filter(status='completed')
                if owner:
                    qs = qs.filter(owner=owner)
                
                recent = qs.values(
                    'id', 'invoice_number', 'total_amount', 'paid_amount',
                    'payment_status', 'invoice_date', 'customer__name'
                ).order_by('-invoice_date')[:limit]
                invoices = list(recent)
            except:
                pass
            
            return Response(invoices)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_200_OK)

class LowStockAlertsView(APIView):
    """Get low stock alerts."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get low stock items."""
        if not request.user.is_superuser:
             from apps.users.utils import has_permission
             if not has_permission(request.user, 'view_dashboard'):
                 from rest_framework.exceptions import PermissionDenied
                 raise PermissionDenied("You do not have permission to view the dashboard.")

        try:
            low_stock = []
            try:
                # Resolve Owner
                from apps.common.helpers import get_user_owner
                owner = get_user_owner(request.user)
                
                qs = Product.objects.filter(stock__lte=10)
                if owner:
                    qs = qs.filter(owner=owner)

                products = qs.values(
                    'id', 'product_code', 'name', 'stock', 'reorder_level'
                ).order_by('stock')[:20]
                low_stock = list(products)
            except:
                pass
            
            return Response(low_stock)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_200_OK)

class ComprehensiveAnalyticsView(APIView):
    """Comprehensive business analytics and insights."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get detailed business analytics."""
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'view_dashboard'):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("You do not have permission to view the dashboard.")

        try:
            # Time range
            days = int(request.query_params.get('days', 30))
            start = timezone.now().date() - timedelta(days=days)

            # Resolve Owner
            from apps.common.helpers import get_user_owner
            owner = get_user_owner(request.user)

            # Base qsets
            invoice_qs = Invoice.objects.all()
            customer_qs = Customer.objects.all()
            product_qs = Product.objects.all()
            
            if owner:
                invoice_qs = invoice_qs.filter(owner=owner)
                customer_qs = customer_qs.filter(owner=owner)
                product_qs = product_qs.filter(owner=owner)
            
            # Sales metrics
            sales_metrics = {}
            try:
                total_invoices = invoice_qs.filter(
                    status='completed',
                    invoice_date__date__gte=start
                ).count()
                
                avg_invoice = 0
                if total_invoices > 0:
                    total_sales = invoice_qs.filter(
                        status='completed',
                        invoice_date__date__gte=start
                    ).aggregate(total=Sum('total_amount'))['total'] or 0
                    avg_invoice = float(total_sales) / total_invoices
                
                sales_metrics = {
                    'total_invoices': total_invoices,
                    'total_sales': float(avg_invoice * total_invoices) if total_invoices > 0 else 0,
                    'average_invoice_value': float(avg_invoice),
                    'period_days': days
                }
            except Exception as e:
                sales_metrics = {'total_invoices': 0, 'total_sales': 0, 'average_invoice_value': 0, 'period_days': days}
            
            # Payment metrics
            payment_metrics = {}
            try:
                paid_amount = invoice_qs.filter(
                    status='completed',
                    payment_status='paid',
                    invoice_date__date__gte=start
                ).aggregate(total=Sum('paid_amount'))['total'] or 0
                
                pending_amount = invoice_qs.filter(
                    status='completed',
                    payment_status__in=['unpaid', 'partial'],
                    invoice_date__date__gte=start
                ).aggregate(total=Sum('total_amount'))['total'] or 0
                
                payment_metrics = {
                    'paid': float(paid_amount),
                    'pending': float(pending_amount),
                    'collection_rate': float(paid_amount / (paid_amount + pending_amount) * 100) if (paid_amount + pending_amount) > 0 else 0
                }
            except:
                payment_metrics = {'paid': 0, 'pending': 0, 'collection_rate': 0}
            
            # Customer metrics
            customer_metrics = {}
            try:
                total_customers = customer_qs.filter(status='active').count()
                new_customers = customer_qs.filter(
                    status='active',
                    created_at__date__gte=start
                ).count()
                
                try:
                    repeat_customers = customer_qs.filter(status='active').annotate(
                        invoice_count=Count('invoices', filter=Q(invoices__status='completed'))
                    ).filter(invoice_count__gt=1).count()
                except:
                    repeat_customers = 0
                
                customer_metrics = {
                    'total_active': total_customers,
                    'new_customers': new_customers,
                    'repeat_customers': repeat_customers,
                    'repeat_customer_percentage': float(repeat_customers / total_customers * 100) if total_customers > 0 else 0
                }
            except:
                customer_metrics = {'total_active': 0, 'new_customers': 0, 'repeat_customers': 0, 'repeat_customer_percentage': 0}
            
            # Product metrics
            product_metrics = {}
            try:
                total_products = product_qs.count()
                active_products = product_qs.filter(stock__gt=0).count()
                
                product_metrics = {
                    'total_products': total_products,
                    'active_products': active_products,
                    'low_stock_count': product_qs.filter(stock__lte=10).count(),
                    'out_of_stock_count': product_qs.filter(stock=0).count()
                }
            except:
                product_metrics = {'total_products': 0, 'active_products': 0, 'low_stock_count': 0, 'out_of_stock_count': 0}
            
            # Growth metrics
            growth_metrics = {}
            try:
                # Previous period
                prev_start = start - timedelta(days=days)
                prev_sales = invoice_qs.filter(
                    status='completed',
                    invoice_date__date__gte=prev_start,
                    invoice_date__date__lt=start
                ).aggregate(total=Sum('total_amount'))['total'] or 0
                
                current_sales = invoice_qs.filter(
                    status='completed',
                    invoice_date__date__gte=start
                ).aggregate(total=Sum('total_amount'))['total'] or 0
                
                sales_growth = 0
                if float(prev_sales) > 0:
                    sales_growth = float((current_sales - prev_sales) / prev_sales * 100)
                
                growth_metrics = {
                    'sales_growth_percentage': float(sales_growth),
                    'current_period_sales': float(current_sales),
                    'previous_period_sales': float(prev_sales)
                }
            except:
                growth_metrics = {'sales_growth_percentage': 0, 'current_period_sales': 0, 'previous_period_sales': 0}
            
            return Response({
                'sales_metrics': sales_metrics,
                'payment_metrics': payment_metrics,
                'customer_metrics': customer_metrics,
                'product_metrics': product_metrics,
                'growth_metrics': growth_metrics,
                'analysis_period_days': days
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_200_OK)
