from django.test import TestCase
from apps.customer.models import Customer
from apps.billing.models import Invoice, InvoiceItem
from apps.product.models import Product, Category
from decimal import Decimal

class BillingModelTests(TestCase):
    """Test Billing models."""

    def setUp(self):
        self.customer = Customer.objects.create(
            phone='9876543210',
            name='Test Customer'
        )
        self.category = Category.objects.create(name='Electronics')
        self.product = Product.objects.create(
            product_code='PROD001',
            name='Test Product',
            category=self.category,
            unit_price=Decimal('1000.00'),
            tax_rate=Decimal('18.00'),
            stock=100
        )

    def test_invoice_creation(self):
        """Test invoice creation."""
        invoice = Invoice.objects.create(
            invoice_number='INV-20251207-TEST',
            customer=self.customer,
            billing_mode='with_gst'
        )
        self.assertEqual(invoice.customer, self.customer)
        self.assertEqual(invoice.status, 'draft')

    def test_calculate_tax(self):
        """Test tax calculation."""
        invoice = Invoice.objects.create(
            invoice_number='INV-20251207-TAX',
            customer=self.customer,
            billing_mode='with_gst',
            subtotal=Decimal('1000.00'),
            tax_rate=Decimal('18.00')
        )
        invoice.calculate_tax()
        self.assertEqual(invoice.cgst_amount, Decimal('90.00'))
        self.assertEqual(invoice.sgst_amount, Decimal('90.00'))

    def test_invoice_item_calculation(self):
        """Test invoice item line total."""
        invoice = Invoice.objects.create(
            invoice_number='INV-20251207-ITEM',
            customer=self.customer
        )
        item = InvoiceItem.objects.create(
            invoice=invoice,
            product=self.product,
            product_name='Test Product',
            product_code='PROD001',
            quantity=2,
            unit_price=Decimal('1000.00'),
            tax_rate=Decimal('18.00')
        )
        item.calculate_line_total()
        self.assertEqual(item.line_total, Decimal('2360.00'))
