"""
Tests for users module covering roles, permissions, and assignments.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from .models import Role, Permission, RolePermission, UserRole
from django.db import IntegrityError

User = get_user_model()

class RoleModelTests(TestCase):
    """Test Role model."""
    
    def test_create_role(self):
        """Test creating a role."""
        role = Role.objects.create(name="Admin", description="Administrator")
        self.assertEqual(role.name, "Admin")
    
    def test_role_unique_name(self):
        """Test role name is unique."""
        Role.objects.create(name="Admin")
        
        with self.assertRaises(Exception):
            Role.objects.create(name="Admin")

class PermissionModelTests(TestCase):
    """Test Permission model."""
    
    def test_create_permission(self):
        """Test creating a permission."""
        permission = Permission.objects.create(
            code="can_edit_products",
            description="Can edit product information"
        )
        self.assertEqual(permission.code, "can_edit_products")
    
    def test_permission_unique_code(self):
        """Test permission code is unique."""
        Permission.objects.create(code="can_delete")
        
        with self.assertRaises(Exception):
            Permission.objects.create(code="can_delete")

class RolePermissionModelTests(TestCase):
    """Test RolePermission through model."""
    
    def setUp(self):
        self.role = Role.objects.create(name="Manager")
        self.permission = Permission.objects.create(code="can_edit_orders")
    
    def test_assign_permission_to_role(self):
        """Test assigning permission to role."""
        assignment = RolePermission.objects.create(role=self.role, permission=self.permission)
        self.assertEqual(assignment.role, self.role)
        self.assertEqual(assignment.permission, self.permission)
    
    def test_duplicate_assignment_prevented(self):
        """Test duplicate role-permission assignments are prevented."""
        RolePermission.objects.create(role=self.role, permission=self.permission)
        
        with self.assertRaises(IntegrityError):
            RolePermission.objects.create(role=self.role, permission=self.permission)

class UserRoleModelTests(TestCase):
    """Test UserRole through model."""
    
    def setUp(self):
        self.user = User.objects.create_user(phone='9876543210', password='test123')
        self.role = Role.objects.create(name="Admin")
    
    def test_assign_role_to_user(self):
        """Test assigning role to user."""
        assignment = UserRole.objects.create(user=self.user, role=self.role)
        self.assertEqual(assignment.user, self.user)
        self.assertEqual(assignment.role, self.role)
    
    def test_duplicate_user_role_prevented(self):
        """Test duplicate user-role assignments are prevented."""
        UserRole.objects.create(user=self.user, role=self.role)
        
        with self.assertRaises(IntegrityError):
            UserRole.objects.create(user=self.user, role=self.role)

class CreateRoleViewTests(TestCase):
    """Test CreateRole view."""
    
    def setUp(self):
        self.client = Client()
        self.create_role_url = '/api/users/roles/'  # Adjust based on actual URL
        self.admin_user = User.objects.create_superuser(phone='9999999999', password='admin123')
    
    def test_create_role_requires_auth(self):
        """Test creating role requires authentication."""
        response = self.client.post(
            self.create_role_url,
            {'name': 'Manager'},
            content_type='application/json'
        )
        # Should be unauthorized or forbidden
        self.assertNotEqual(response.status_code, 201)
    
    def test_create_role_by_admin(self):
        """Test admin can create role."""
        self.client.force_login(self.admin_user)
        
        response = self.client.post(
            self.create_role_url,
            {'name': 'Manager', 'description': 'Manager role'},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Role.objects.filter(name='Manager').exists())

class CreatePermissionViewTests(TestCase):
    """Test CreatePermission view."""
    
    def setUp(self):
        self.client = Client()
        self.create_perm_url = '/api/users/permissions/'  # Adjust based on actual URL
        self.admin_user = User.objects.create_superuser(phone='9999999999', password='admin123')
    
    def test_create_permission_by_admin(self):
        """Test admin can create permission."""
        self.client.force_login(self.admin_user)
        
        response = self.client.post(
            self.create_perm_url,
            {'code': 'can_edit_products', 'description': 'Can edit products'},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Permission.objects.filter(code='can_edit_products').exists())

class AssignPermissionToRoleViewTests(TestCase):
    """Test AssignPermissionToRole view with duplicate handling."""
    
    def setUp(self):
        self.client = Client()
        self.assign_perm_url = '/api/users/assign-permission/'  # Adjust based on actual URL
        self.admin_user = User.objects.create_superuser(phone='9999999999', password='admin123')
        
        self.role = Role.objects.create(name='Manager')
        self.permission = Permission.objects.create(code='can_edit_orders')
    
    def test_assign_permission_to_role(self):
        """Test assigning permission to role."""
        self.client.force_login(self.admin_user)
        
        response = self.client.post(
            self.assign_perm_url,
            {'role': self.role.id, 'permission': self.permission.id},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            RolePermission.objects.filter(role=self.role, permission=self.permission).exists()
        )
    
    def test_duplicate_permission_assignment_returns_400(self):
        """Test duplicate assignment returns friendly error."""
        # Create initial assignment
        RolePermission.objects.create(role=self.role, permission=self.permission)
        
        self.client.force_login(self.admin_user)
        
        # Try to assign again
        response = self.client.post(
            self.assign_perm_url,
            {'role': self.role.id, 'permission': self.permission.id},
            content_type='application/json'
        )
        
        # Should return 400 (bad request), not 500 (server error)
        self.assertEqual(response.status_code, 400)
        self.assertIn('already assigned', response.json()['detail'].lower())

class AssignRoleToUserViewTests(TestCase):
    """Test AssignRoleToUser view with duplicate handling."""
    
    def setUp(self):
        self.client = Client()
        self.assign_role_url = '/api/users/assign-role/'  # Adjust based on actual URL
        self.admin_user = User.objects.create_superuser(phone='9999999999', password='admin123')
        
        self.user = User.objects.create_user(phone='9876543210', password='test123')
        self.role = Role.objects.create(name='Manager')
    
    def test_assign_role_to_user(self):
        """Test assigning role to user."""
        self.client.force_login(self.admin_user)
        
        response = self.client.post(
            self.assign_role_url,
            {'user': self.user.id, 'role': self.role.id},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        self.assertTrue(UserRole.objects.filter(user=self.user, role=self.role).exists())
    
    def test_duplicate_role_assignment_returns_400(self):
        """Test duplicate assignment returns friendly error."""
        # Create initial assignment
        UserRole.objects.create(user=self.user, role=self.role)
        
        self.client.force_login(self.admin_user)
        
        # Try to assign again
        response = self.client.post(
            self.assign_role_url,
            {'user': self.user.id, 'role': self.role.id},
            content_type='application/json'
        )
        
        # Should return 400 (bad request), not 500 (server error)
        self.assertEqual(response.status_code, 400)
        self.assertIn('already assigned', response.json()['detail'].lower())

class UserListViewTests(TestCase):
    """Test UserList view with prefetch_related optimization."""
    
    def setUp(self):
        self.client = Client()
        self.list_url = '/api/users/list/'  # Adjust based on actual URL
        self.admin_user = User.objects.create_superuser(phone='9999999999', password='admin123')
        
        # Create users with roles
        self.user1 = User.objects.create_user(phone='9876543210', password='test123')
        self.role = Role.objects.create(name='Manager')
        UserRole.objects.create(user=self.user1, role=self.role)
    
    def test_list_users_returns_roles(self):
        """Test user list returns structured role data."""
        self.client.force_login(self.admin_user)
        
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Should have user with roles
        user_data = next((u for u in data if u['phone'] == '9876543210'), None)
        self.assertIsNotNone(user_data)
        self.assertEqual(len(user_data['roles']), 1)
        self.assertEqual(user_data['roles'][0]['name'], 'Manager')

class RoleListViewTests(TestCase):
    """Test RoleList view."""
    
    def setUp(self):
        self.client = Client()
        self.list_url = '/api/users/roles/'  # Adjust based on actual URL
        self.admin_user = User.objects.create_superuser(phone='9999999999', password='admin123')
        
        Role.objects.create(name='Admin')
        Role.objects.create(name='Manager')
    
    def test_list_roles_by_admin(self):
        """Test admin can list roles."""
        self.client.force_login(self.admin_user)
        
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data), 2)

class PermissionListViewTests(TestCase):
    """Test PermissionList view."""
    
    def setUp(self):
        self.client = Client()
        self.list_url = '/api/users/permissions/'  # Adjust based on actual URL
        self.admin_user = User.objects.create_superuser(phone='9999999999', password='admin123')
        
        Permission.objects.create(code='can_edit')
        Permission.objects.create(code='can_delete')
    
    def test_list_permissions_by_admin(self):
        """Test admin can list permissions."""
        self.client.force_login(self.admin_user)
        
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data), 2)

