from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Product, Category
from .serializers import ProductSerializer, CategorySerializer
from apps.auth_app.permissions import IsAdminOrHasPermission, IsAuthenticated

class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for product list."""
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

class ProductListCreate(APIView):
    """List all products with filtering, searching, and pagination. Create new products."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get list of products with filtering, searching, and pagination."""
        queryset = Product.objects.select_related("category").all()

        # Filter by Owner
        if request.user.is_authenticated:
            if not request.user.is_super_admin:
                from apps.common.helpers import get_user_owner
                owner = get_user_owner(request.user)
                if owner:
                    queryset = queryset.filter(owner=owner)

        category_id = request.query_params.get("category", None)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Filter by active status
        is_active = request.query_params.get("is_active", None)
        if is_active in ["true", "True", "1"]:
            queryset = queryset.filter(is_active=True)
        elif is_active in ["false", "False", "0"]:
            queryset = queryset.filter(is_active=False)
        
        # Search by name, product_code, or supplier
        search = request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(product_code__icontains=search)
            )
        
        # Ordering
        ordering = request.query_params.get("ordering", "-created_at")
        queryset = queryset.order_by(ordering)
        
        # Pagination
        paginator = StandardResultsSetPagination()
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        serializer = ProductSerializer(paginated_queryset, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        """Create new product. Requires authentication."""
        # Permission check
        if not request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(request.user, 'manage_inventory'):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("You do not have permission to manage inventory.")

        if not request.user or not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            try:
                from apps.common.helpers import get_user_owner
                owner = get_user_owner(request.user)
                serializer.save(owner=owner)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response(
                    {"detail": str(e)}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProductRetrieveUpdateDelete(APIView):
    """Retrieve, update (PUT/PATCH), or delete a single product."""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        """Get product by ID and ensure it belongs to the current user's owner."""
        user = self.request.user
        if user.is_super_admin:
            return get_object_or_404(Product, pk=pk)
            
        from apps.common.helpers import get_user_owner
        owner = get_user_owner(user)
        return get_object_or_404(Product, pk=pk, owner=owner)

    def get(self, request, pk):
        """Retrieve a single product."""
        product = self.get_object(pk)
        serializer = ProductSerializer(product)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        """Full update (replace entire object). Requires authentication."""
        if not request.user.is_superuser:
             from apps.users.utils import has_permission
             if not has_permission(request.user, 'manage_inventory'):
                 from rest_framework.exceptions import PermissionDenied
                 raise PermissionDenied("You do not have permission to manage inventory.")

        if not request.user or not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        product = self.get_object(pk)
        serializer = ProductSerializer(product, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        """Partial update (update specific fields). Requires authentication."""
        if not request.user.is_superuser:
             from apps.users.utils import has_permission
             if not has_permission(request.user, 'manage_inventory'):
                 from rest_framework.exceptions import PermissionDenied
                 raise PermissionDenied("You do not have permission to manage inventory.")

        if not request.user or not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        product = self.get_object(pk)
        serializer = ProductSerializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Delete a product. Requires authentication."""
        if not request.user.is_superuser:
             from apps.users.utils import has_permission
             if not has_permission(request.user, 'manage_inventory'):
                 from rest_framework.exceptions import PermissionDenied
                 raise PermissionDenied("You do not have permission to manage inventory.")

        if not request.user or not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        product = self.get_object(pk)
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class CategoryListCreate(APIView):
    """List all categories or create a new one."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get all categories ordered by creation date."""
        queryset = Category.objects.all()

        # Filter by Owner
        if request.user.is_authenticated:
            if not request.user.is_super_admin:
                from apps.common.helpers import get_user_owner
                owner = get_user_owner(request.user)
                if owner:
                    queryset = queryset.filter(owner=owner)

        categories = queryset.order_by("created_at")
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Create new category. Requires authentication."""
        if not request.user.is_superuser:
             from apps.users.utils import has_permission
             if not has_permission(request.user, 'manage_inventory'):
                 from rest_framework.exceptions import PermissionDenied
                 raise PermissionDenied("You do not have permission to manage inventory.")

        if not request.user or not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            try:
                from apps.common.helpers import get_user_owner
                owner = get_user_owner(request.user)
                serializer.save(owner=owner)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response(
                    {"detail": str(e)}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CategoryRetrieveUpdateDelete(APIView):
    """Retrieve, update (PUT/PATCH), or delete a single category."""
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        """Get category by ID and ensure it belongs to the current user's owner."""
        user = self.request.user
        if user.is_super_admin:
            return get_object_or_404(Category, pk=pk)
            
        from apps.common.helpers import get_user_owner
        owner = get_user_owner(user)
        return get_object_or_404(Category, pk=pk, owner=owner)

    def get(self, request, pk):
        """Retrieve a single category."""
        category = self.get_object(pk)
        serializer = CategorySerializer(category)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        """Full update. Requires authentication."""
        if not request.user.is_superuser:
             from apps.users.utils import has_permission
             if not has_permission(request.user, 'manage_inventory'):
                 from rest_framework.exceptions import PermissionDenied
                 raise PermissionDenied("You do not have permission to manage inventory.")

        if not request.user or not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        category = self.get_object(pk)
        serializer = CategorySerializer(category, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Delete a category. Requires authentication."""
        if not request.user.is_superuser:
             from apps.users.utils import has_permission
             if not has_permission(request.user, 'manage_inventory'):
                 from rest_framework.exceptions import PermissionDenied
                 raise PermissionDenied("You do not have permission to manage inventory.")

        if not request.user or not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        category = self.get_object(pk)
        # Optional: Check if used by products before deleting? 
        # Django's on_delete=models.SET_NULL or PROTECT would handle it. 
        # Model has SET_NULL, so products will just lose category.
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

from apps.common.models import AppNotification
from apps.purchase.models import SupplierNotificationLog
from apps.common.models import CompanyProfile, SystemSettings
from django.db.models import F

class CheckStockAlertsView(APIView):
    """
    Manually trigger low stock checks.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        
        # Products that need reordering
        # Use owner filter if applicable
        products = Product.objects.filter(is_active=True).select_related('preferred_supplier')
        
        if not user.is_super_admin:
            from apps.common.helpers import get_user_owner
            owner = get_user_owner(user)
            if owner:
                products = products.filter(owner=owner)
        
        low_stock_products = products.filter(stock__lte=F('reorder_level'))
        
        alerts_generated = 0
        notifications_sent = 0
        
        for product in low_stock_products:
            # 1. Notify Owner (create in-app notification)
            # Check if recent unread notification exists to avoid spam
            existing_notif = AppNotification.objects.filter(
                user=user,
                title="Low Stock Alert",
                message__contains=product.name,
                is_read=False
            ).exists()
            
            if not existing_notif:
                AppNotification.objects.create(
                    user=user,
                    title="Low Stock Alert",
                    message=f"Product '{product.name}' is low on stock (Current: {product.stock}, Reorder Level: {product.reorder_level}).",
                    related_link=f"/inventory?status=Low%20Stock"
                )
                alerts_generated += 1
            
            # 2. Auto-Intimate Supplier (if configured)
            # Check if company settings allow auto-intimate
            try:
                from apps.common.helpers import get_user_owner
                owner = get_user_owner(user)
                profile = CompanyProfile.objects.get(owner=owner)
                # Ensure notification_settings is a dict
                if not isinstance(profile.notification_settings, dict):
                    profile.notification_settings = {}
                auto_intimate = profile.notification_settings.get('auto_intimate_suppliers', False)
            except (CompanyProfile.DoesNotExist, AttributeError):
                auto_intimate = False
                profile = None
                
            if auto_intimate and product.preferred_supplier and profile:
                # Check cooldown (e.g., don't message same supplier for same product today)
                from django.utils import timezone
                today = timezone.now().date()
                already_sent = SupplierNotificationLog.objects.filter(
                    supplier=product.preferred_supplier,
                    product=product,
                    created_at__date=today
                ).exists()
                
                if not already_sent:
                    # Construct Message
                    supplier = product.preferred_supplier
                    
                    # Template replacement
                    message = f"""Hello {supplier.name},
We need {product.reorder_quantity} units of {product.name}.
Current stock is low ({product.stock}).
Please confirm availability.
– {profile.company_name}"""

                    # Log the "sending"
                    SupplierNotificationLog.objects.create(
                        supplier=supplier,
                        product=product,
                        notification_type='low_stock',
                        sent_via='simulated', # Mocking SMS/Email
                        status='success',
                        message_content=message
                    )
                    notifications_sent += 1
                    
        return Response({
            'detail': 'Stock check complete', 
            'alerts_generated': alerts_generated,
            'supplier_notifications': notifications_sent
        })
