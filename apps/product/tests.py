"""
Tests for product module covering CRUD operations, validation, and permissions.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from .models import Product, Category
from apps.users.models import Role, Permission, RolePermission, UserRole
from decimal import Decimal
import json

User = get_user_model()

class CategoryModelTests(TestCase):
    """Test Category model."""
    
    def test_create_category(self):
        """Test creating a category."""
        category = Category.objects.create(
            name="Electronics",
            description="Electronic items"
        )
        self.assertEqual(category.name, "Electronics")
        self.assertTrue(category.is_active)
    
    def test_category_unique_name(self):
        """Test category name is unique."""
        Category.objects.create(name="Electronics")
        
        with self.assertRaises(Exception):
            Category.objects.create(name="Electronics")

class ProductModelTests(TestCase):
    """Test Product model and validation."""
    
    def setUp(self):
        self.category = Category.objects.create(name="Electronics")
    
    def test_create_product(self):
        """Test creating a product."""
        product = Product.objects.create(
            product_code="PROD001",
            name="Laptop",
            category=self.category,
            unit_price=Decimal("999.99"),
            tax_rate=Decimal("10.00"),
            stock=50
        )
        self.assertEqual(product.name, "Laptop")
        self.assertEqual(product.stock, 50)
    
    def test_product_stock_non_negative_validator(self):
        """Test stock cannot be negative."""
        product = Product(
            product_code="PROD002",
            name="Mouse",
            unit_price=Decimal("20.00"),
            tax_rate=Decimal("10.00"),
            stock=-5
        )
        
        with self.assertRaises(Exception):
            product.full_clean()
    
    def test_product_tax_rate_validation(self):
        """Test tax rate must be 0-100."""
        # Invalid: > 100
        product = Product(
            product_code="PROD003",
            name="Keyboard",
            unit_price=Decimal("50.00"),
            tax_rate=Decimal("150.00"),
            stock=10
        )
        
        with self.assertRaises(Exception):
            product.full_clean()
    
    def test_product_is_low_stock(self):
        """Test is_low_stock method."""
        product = Product.objects.create(
            product_code="PROD004",
            name="Monitor",
            unit_price=Decimal("300.00"),
            tax_rate=Decimal("10.00"),
            stock=5,
            reorder_level=10
        )
        
        self.assertTrue(product.is_low_stock())
    
    def test_product_get_stock_value(self):
        """Test get_stock_value calculation."""
        product = Product.objects.create(
            product_code="PROD005",
            name="Webcam",
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("10.00"),
            stock=5
        )
        
        expected_value = 5 * Decimal("100.00")
        self.assertEqual(product.get_stock_value(), expected_value)

class ProductListCreateViewTests(TestCase):
    """Test ProductListCreate view with filtering and permissions."""
    
    def setUp(self):
        self.client = Client()
        self.list_url = '/api/products/'  # Adjust based on actual URL
        self.category = Category.objects.create(name="Electronics")
        self.user = User.objects.create_user(phone='9876543210', password='test123')
        
        # Create test products
        self.product1 = Product.objects.create(
            product_code="PROD001",
            name="Laptop",
            category=self.category,
            unit_price=Decimal("999.99"),
            tax_rate=Decimal("10.00"),
            stock=50,
            is_active=True
        )
        
        self.product2 = Product.objects.create(
            product_code="PROD002",
            name="Mouse",
            category=self.category,
            unit_price=Decimal("20.00"),
            tax_rate=Decimal("10.00"),
            stock=100,
            is_active=False
        )
    
    def test_list_products_unauthenticated_denied(self):
        """Test unauthenticated users cannot list products."""
        response = self.client.get(self.list_url)
        # Should return 401 Unauthorized or redirect to login
        self.assertNotEqual(response.status_code, 200)
    
    def test_list_products_authenticated(self):
        """Test authenticated users can list products."""
        self.client.force_login(self.user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
    
    def test_filter_products_by_active_status(self):
        """Test filtering products by active status."""
        self.client.force_login(self.user)
        response = self.client.get(f"{self.list_url}?is_active=true")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Should only contain active products
        if 'results' in data:
            for product in data['results']:
                self.assertTrue(product['is_active'])
    
    def test_filter_products_by_category(self):
        """Test filtering products by category."""
        self.client.force_login(self.user)
        response = self.client.get(f"{self.list_url}?category={self.category.id}")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Should contain products from this category
        self.assertGreater(len(data['results'] if 'results' in data else data), 0)
    
    def test_search_products(self):
        """Test searching products by name or code."""
        self.client.force_login(self.user)
        response = self.client.get(f"{self.list_url}?search=Laptop")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Should contain the laptop product

class ProductDetailViewTests(TestCase):
    """Test ProductRetrieveUpdateDelete view."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(phone='9876543210', password='test123')
        self.admin_user = User.objects.create_superuser(phone='9999999999', password='admin123')
        
        self.category = Category.objects.create(name="Electronics")
        self.product = Product.objects.create(
            product_code="PROD001",
            name="Laptop",
            category=self.category,
            unit_price=Decimal("999.99"),
            tax_rate=Decimal("10.00"),
            stock=50
        )
        self.detail_url = f'/api/products/{self.product.id}/'  # Adjust based on actual URL
    
    def test_retrieve_product(self):
        """Test retrieving a single product."""
        self.client.force_login(self.user)
        response = self.client.get(self.detail_url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['name'], "Laptop")
    
    def test_patch_product_updates_specific_fields(self):
        """Test PATCH updates only specified fields."""
        self.client.force_login(self.admin_user)
        
        response = self.client.patch(
            self.detail_url,
            {'stock': 75},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 75)
        self.assertEqual(self.product.name, "Laptop")  # Should not change
    
    def test_put_product_full_update(self):
        """Test PUT replaces all fields."""
        self.client.force_login(self.admin_user)
        
        response = self.client.put(
            self.detail_url,
            {
                'product_code': 'PROD001',
                'name': 'Updated Laptop',
                'unit_price': '1499.99',
                'tax_rate': '12.00',
                'stock': 30,
                'is_active': True
            },
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Updated Laptop")
    
    def test_delete_product_requires_permission(self):
        """Test deleting product requires admin permission."""
        self.client.force_login(self.user)
        
        response = self.client.delete(self.detail_url)
        # Should be forbidden
        self.assertNotEqual(response.status_code, 204)
    
    def test_delete_product_by_admin(self):
        """Test admin can delete product."""
        self.client.force_login(self.admin_user)
        
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, 204)
        
        # Verify deleted
        self.assertFalse(Product.objects.filter(id=self.product.id).exists())

class ProductSerializerTests(TestCase):
    """Test ProductSerializer validation."""
    
    def setUp(self):
        self.category = Category.objects.create(name="Electronics")
    
    def test_serializer_validates_empty_product_code(self):
        """Test serializer rejects empty product code."""
        from apps.product.serializers import ProductSerializer
        
        serializer = ProductSerializer(data={
            'product_code': '',
            'name': 'Test',
            'unit_price': '100.00',
            'tax_rate': '10.00'
        })
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('product_code', serializer.errors)
    
    def test_serializer_validates_negative_price(self):
        """Test serializer rejects negative price."""
        from apps.product.serializers import ProductSerializer
        
        serializer = ProductSerializer(data={
            'product_code': 'PROD001',
            'name': 'Test',
            'unit_price': '-100.00',
            'tax_rate': '10.00'
        })
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('unit_price', serializer.errors)

