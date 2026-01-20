from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.pagination import PageNumberPagination
from django.db import transaction
from .models import Payment, PaymentRefund, PaymentMethod
from .serializers import PaymentSerializer, PaymentRefundSerializer, PaymentMethodSerializer
from apps.auth_app.permissions import IsAuthenticated
import uuid
from decimal import Decimal

class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class PaymentMethodListView(ListCreateAPIView):
    """List payment methods."""
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsAuthenticated]

class PaymentListCreateView(ListCreateAPIView):
    """List and create payments."""
    queryset = Payment.objects.select_related('invoice', 'payment_method')
    serializer_class = PaymentSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Payment.objects.select_related('invoice', 'payment_method')
        
        # Filter by invoice
        invoice_id = self.request.query_params.get('invoice_id')
        if invoice_id:
            queryset = queryset.filter(invoice_id=invoice_id)
        
        # Filter by status
        payment_status = self.request.query_params.get('status')
        if payment_status:
            queryset = queryset.filter(status=payment_status)
        
        # Filter by payment method
        method = self.request.query_params.get('method')
        if method:
            queryset = queryset.filter(payment_method__name=method)
        
        return queryset.order_by('-created_at')

    @transaction.atomic
    def perform_create(self, serializer):
        payment_id = f"PAY-{uuid.uuid4().hex[:12].upper()}"
        payment = serializer.save(
            payment_id=payment_id,
            created_by_id=self.request.user.id if hasattr(self.request, 'user') else None
        )
        
        # Update invoice payment status
        invoice = payment.invoice
        invoice.paid_amount += payment.amount
        
        if invoice.paid_amount >= invoice.total_amount:
            invoice.payment_status = 'paid'
        elif invoice.paid_amount > 0:
            invoice.payment_status = 'partial'
        
        invoice.save()
        
        # Log the updated pending amount for the customer
        customer = invoice.customer
        if customer:
            pending_amount = customer.get_pending_amount()

class PaymentDetailView(RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a payment."""
    queryset = Payment.objects.select_related('invoice', 'payment_method')
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

class PaymentRefundListCreateView(ListCreateAPIView):
    """List and create refunds."""
    queryset = PaymentRefund.objects.select_related('payment')
    serializer_class = PaymentRefundSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def perform_create(self, serializer):
        refund_id = f"REF-{uuid.uuid4().hex[:12].upper()}"
        refund = serializer.save(
            refund_id=refund_id,
            created_by_id=self.request.user.id if hasattr(self.request, 'user') else None
        )
        
        # Update payment status if refunded
        if refund.amount >= refund.payment.amount:
            refund.payment.status = 'refunded'
            refund.payment.save()
            
            # Update invoice paid_amount
            invoice = refund.payment.invoice
            invoice.paid_amount -= refund.amount
            
            # Recalculate payment status
            if invoice.paid_amount <= 0:
                invoice.payment_status = 'unpaid'
                invoice.paid_amount = Decimal('0')
            elif invoice.paid_amount >= invoice.total_amount:
                invoice.payment_status = 'paid'
            else:
                invoice.payment_status = 'partial'
            
            invoice.save()
            
            # Log the updated pending amount for the customer
            customer = invoice.customer
            if customer:
                pending_amount = customer.get_pending_amount()

class PaymentProcessView(APIView):
    """Process payment (initialize transaction)."""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """Process payment."""
        from apps.billing.models import Invoice
        
        invoice_id = request.data.get('invoice_id')
        amount = Decimal(str(request.data.get('amount', 0)))
        payment_method_id = request.data.get('payment_method_id')
        
        try:
            invoice = Invoice.objects.get(id=invoice_id)
            payment_method = PaymentMethod.objects.get(id=payment_method_id)
        except (Invoice.DoesNotExist, PaymentMethod.DoesNotExist):
            return Response({'detail': 'Invalid invoice or payment method'}, status=status.HTTP_404_NOT_FOUND)
        
        # Create payment record
        payment_id = f"PAY-{uuid.uuid4().hex[:12].upper()}"
        payment = Payment.objects.create(
            payment_id=payment_id,
            invoice=invoice,
            amount=amount,
            payment_method=payment_method,
            status='processing',
            created_by_id=request.user.id if hasattr(request, 'user') else None
        )
        
        # If cash/cheque, mark as pending. If gateway, initiate gateway
        if payment_method.requires_gateway:
            # TODO: Initiate Razorpay/Stripe payment gateway
            pass
        
        serializer = PaymentSerializer(payment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class PaymentCompleteView(APIView):
    """Mark payment as completed."""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, payment_id):
        """Complete payment."""
        try:
            payment = Payment.objects.get(id=payment_id)
        except Payment.DoesNotExist:
            return Response({'detail': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)
        
        payment.status = 'completed'
        payment.save()
        
        # Update invoice
        invoice = payment.invoice
        invoice.paid_amount += payment.amount
        if invoice.paid_amount >= invoice.total_amount:
            invoice.payment_status = 'paid'
        else:
            invoice.payment_status = 'partial'
        invoice.save()
        
        serializer = PaymentSerializer(payment)
        return Response(serializer.data)
