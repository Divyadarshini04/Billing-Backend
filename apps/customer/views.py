from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.db.models import Q
from .models import Customer, CustomerAddress, LoyaltyTransaction, LoyaltySettings
from .serializers import CustomerSerializer, CustomerAddressSerializer, LoyaltyTransactionSerializer, LoyaltySettingsSerializer
from apps.auth_app.permissions import IsAuthenticated
# from apps.common.utils import get_user_owner

class LoyaltySettingsView(APIView):
    """
    Get or update global loyalty settings.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_superuser:
             from apps.users.utils import has_permission
             if not has_permission(request.user, 'view_loyalty'):
                 from rest_framework.exceptions import PermissionDenied
                 raise PermissionDenied("You do not have permission to view loyalty settings.")

        settings = LoyaltySettings.get_settings()
        serializer = LoyaltySettingsSerializer(settings)
        return Response(serializer.data)

    def post(self, request):
        if not request.user.is_superuser:
             from apps.users.utils import has_permission
             if not has_permission(request.user, 'manage_loyalty'):
                 from rest_framework.exceptions import PermissionDenied
                 raise PermissionDenied("You do not have permission to manage loyalty settings.")

        settings = LoyaltySettings.get_settings()
        serializer = LoyaltySettingsSerializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class CustomerListCreateView(ListCreateAPIView):
    """List all customers and create new customers."""
    queryset = Customer.objects.prefetch_related('addresses')
    serializer_class = CustomerSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """Override create to provide better error handling."""
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise

    def perform_create(self, serializer):
        # Permission check
        if not self.request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(self.request.user, 'manage_customers'):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("You do not have permission to manage customers.")

        from apps.common.helpers import get_user_owner
        owner = get_user_owner(self.request.user)
        serializer.save(owner=owner)

    def get_queryset(self):
        user = self.request.user
        queryset = Customer.objects.prefetch_related('addresses')
        
        # Filter by Owner
        if user.is_authenticated:
            if user.is_super_admin:
                pass # Super admin sees all
            else:
                from apps.common.helpers import get_user_owner
                owner = get_user_owner(user)
                if owner:
                    queryset = queryset.filter(owner=owner)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by customer type
        customer_type = self.request.query_params.get('type')
        if customer_type:
            queryset = queryset.filter(customer_type=customer_type)
        
        # Filter by loyalty tier
        tier = self.request.query_params.get('tier')
        if tier:
            queryset = queryset.filter(loyalty_tier=tier)
        
        # Search by phone, email, name, or GSTIN
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(phone__icontains=search) |
                Q(email__icontains=search) |
                Q(name__icontains=search) |
                Q(gstin__icontains=search)
            )
        
        return queryset.order_by('-created_at')

class CustomerDetailView(RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a customer."""
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Customer.objects.prefetch_related('addresses')
        if not user.is_super_admin:
            from apps.common.helpers import get_user_owner
            owner = get_user_owner(user)
            if owner:
                queryset = queryset.filter(owner=owner)
        return queryset

    def perform_update(self, serializer):
        if not self.request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(self.request.user, 'manage_customers'):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("You do not have permission to manage customers.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(self.request.user, 'manage_customers'):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("You do not have permission to manage customers.")
        instance.delete()

class CustomerAddressListCreateView(APIView):
    """List and create addresses for a customer."""
    permission_classes = [IsAuthenticated]

    def get_customer(self, customer_id):
        user = self.request.user
        if user.is_super_admin:
            return get_object_or_404(Customer, id=customer_id)
        from apps.common.helpers import get_user_owner
        owner = get_user_owner(user)
        return get_object_or_404(Customer, id=customer_id, owner=owner)

    def get(self, request, customer_id):
        """Get all addresses for a customer."""
        customer = self.get_customer(customer_id)
        addresses = CustomerAddress.objects.filter(customer=customer)
        serializer = CustomerAddressSerializer(addresses, many=True)
        return Response(serializer.data)

    def post(self, request, customer_id):
        """Create a new address for a customer."""
        customer = self.get_customer(customer_id)
        serializer = CustomerAddressSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(customer=customer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomerAddressDetailView(RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete an address."""
    serializer_class = CustomerAddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = CustomerAddress.objects.all()
        if not user.is_super_admin:
            from apps.common.helpers import get_user_owner
            owner = get_user_owner(user)
            if owner:
                queryset = queryset.filter(customer__owner=owner)
        return queryset

    def perform_update(self, serializer):
        if not self.request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(self.request.user, 'manage_customers'):
                 from rest_framework.exceptions import PermissionDenied
                 raise PermissionDenied("You do not have permission to manage customers.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.is_superuser:
             from apps.users.utils import has_permission
             if not has_permission(self.request.user, 'manage_customers'):
                 from rest_framework.exceptions import PermissionDenied
                 raise PermissionDenied("You do not have permission to manage customers.")
        instance.delete()

class LoyaltyTransactionListView(ListCreateAPIView):
    """List loyalty transactions for a customer."""
    serializer_class = LoyaltyTransactionSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = LoyaltyTransaction.objects.all()
        
        if not user.is_super_admin:
             from apps.common.helpers import get_user_owner
             owner = get_user_owner(user)
             if owner:
                 queryset = queryset.filter(customer__owner=owner)
             
             from apps.users.utils import has_permission
             if not has_permission(user, 'view_loyalty'):
                 from rest_framework.exceptions import PermissionDenied
                 raise PermissionDenied("You do not have permission to view loyalty transactions.")

        customer_id = self.request.query_params.get('customer_id')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
            
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        if not self.request.user.is_superuser:
             from apps.users.utils import has_permission
             if not has_permission(self.request.user, 'manage_loyalty'):
                 from rest_framework.exceptions import PermissionDenied
                 raise PermissionDenied("You do not have permission to manage loyalty transactions.")

        serializer.save(created_by_id=self.request.user.id if hasattr(self.request, 'user') else None)
