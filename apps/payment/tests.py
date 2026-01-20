from django.test import TestCase
from apps.payment.models import Payment, PaymentMethod, PaymentRefund
from apps.customer.models import Customer
from apps.billing.models import Invoice
from decimal import Decimal

class PaymentModelTests(TestCase):
    """Test Payment models."""

    def setUp(self):
        self.customer = Customer.objects.create(
            phone='9876543210',
            name='Test Customer'
        )
        self.invoice = Invoice.objects.create(
            invoice_number='INV-20251207-PAY',
            customer=self.customer,
            total_amount=Decimal('1000.00')
        )
        self.payment_method = PaymentMethod.objects.create(
            name='cash'
        )

    def test_payment_creation(self):
        """Test payment creation."""
        payment = Payment.objects.create(
            payment_id='PAY-TEST001',
            invoice=self.invoice,
            amount=Decimal('1000.00'),
            payment_method=self.payment_method,
            status='completed'
        )
        self.assertEqual(payment.payment_id, 'PAY-TEST001')
        self.assertEqual(payment.amount, Decimal('1000.00'))

    def test_refund_creation(self):
        """Test refund creation."""
        payment = Payment.objects.create(
            payment_id='PAY-TEST002',
            invoice=self.invoice,
            amount=Decimal('1000.00'),
            payment_method=self.payment_method
        )
        refund = PaymentRefund.objects.create(
            refund_id='REF-TEST001',
            payment=payment,
            amount=Decimal('500.00'),
            reason='Partial refund'
        )
        self.assertEqual(refund.amount, Decimal('500.00'))
