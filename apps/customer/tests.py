from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from .models import Customer, CustomerAddress
import json

User = get_user_model()

class CustomerModelTests(TestCase):
    """Test Customer model."""

    def setUp(self):
        self.customer = Customer.objects.create(
            phone='9876543210',
            name='Test Customer',
            email='test@example.com',
            customer_type='retail'
        )

    def test_customer_creation(self):
        """Test customer creation."""
        self.assertEqual(self.customer.phone, '9876543210')
        self.assertEqual(self.customer.name, 'Test Customer')
        self.assertEqual(self.customer.loyalty_points, 0)
        self.assertEqual(self.customer.loyalty_tier, 'bronze')

    def test_customer_str(self):
        """Test customer string representation."""
        self.assertEqual(str(self.customer), 'Test Customer (9876543210)')

    def test_available_credit(self):
        """Test available credit calculation."""
        self.customer.credit_limit = 10000
        self.customer.current_credit_used = 3000
        self.customer.save()
        self.assertEqual(self.customer.get_available_credit(), 7000)

    def test_add_loyalty_points(self):
        """Test adding loyalty points and tier update."""
        self.customer.add_loyalty_points(1500)
        self.assertEqual(self.customer.loyalty_points, 1500)
        self.assertEqual(self.customer.loyalty_tier, 'silver')

    def test_loyalty_tier_platinum(self):
        """Test platinum tier."""
        self.customer.loyalty_points = 5000
        self.customer._update_loyalty_tier()
        self.assertEqual(self.customer.loyalty_tier, 'platinum')

class CustomerAddressTests(TestCase):
    """Test CustomerAddress model."""

    def setUp(self):
        self.customer = Customer.objects.create(
            phone='9876543210',
            name='Test Customer'
        )

    def test_address_creation(self):
        """Test address creation."""
        address = CustomerAddress.objects.create(
            customer=self.customer,
            type='billing',
            address_line_1='123 Main St',
            city='New York',
            state='NY',
            postal_code='10001'
        )
        self.assertEqual(address.customer, self.customer)
        self.assertEqual(address.type, 'billing')

    def test_default_address_uniqueness(self):
        """Test only one default address per type."""
        addr1 = CustomerAddress.objects.create(
            customer=self.customer,
            type='billing',
            address_line_1='123 Main St',
            city='New York',
            state='NY',
            postal_code='10001',
            is_default=True
        )
        addr2 = CustomerAddress.objects.create(
            customer=self.customer,
            type='billing',
            address_line_1='456 Oak Ave',
            city='Boston',
            state='MA',
            postal_code='02101',
            is_default=True
        )
        addr1.refresh_from_db()
        self.assertFalse(addr1.is_default)
        self.assertTrue(addr2.is_default)
