from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from django.shortcuts import get_object_or_404
from django.db import transaction, IntegrityError
import logging

from .models import User, Role, Permission, RolePermission
from apps.users.models import UserRole
from .serializers import (
    PermissionSerializer,
    RolePermissionSerializer,
    UserRoleSerializer,
    UserSerializer,
    StaffCreateSerializer
)
from apps.auth_app.serializers import UserMinimalSerializer
from .utils import has_permission
from apps.auth_app.permissions import IsAdminOrHasPermission, IsAdmin, IsAuthenticated

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger('audit')

class CreateRole(APIView):
    """Create a new role. Requires 'create_role' permission or superuser."""
    permission_classes = [IsAdminOrHasPermission]
    required_permission = "create_role"

    def post(self, request):
        
        serializer = RoleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            audit_logger.info(f"Role created: name={serializer.data.get('name')}, user={request.user.id}")
            return Response(
                {"detail": "Role created", "data": serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CreatePermission(APIView):
    """Create a new permission. Requires 'create_permission' permission or superuser."""
    permission_classes = [IsAdminOrHasPermission]
    required_permission = "create_permission"

    def post(self, request):
        
        serializer = PermissionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            audit_logger.info(f"Permission created: code={serializer.data.get('code')}, user={request.user.id}")
            return Response(
                {"detail": "Permission created", "data": serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AssignPermissionToRole(APIView):
    """Assign a permission to a role. Requires 'assign_permission' permission or superuser."""
    permission_classes = [IsAdminOrHasPermission]
    required_permission = "assign_permission"

    def post(self, request):
        
        serializer = RolePermissionSerializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save()
                role_id = serializer.data.get('role')
                perm_id = serializer.data.get('permission')
                audit_logger.info(f"Permission assigned to role: role_id={role_id}, permission_id={perm_id}, user={request.user.id}")
                return Response(
                    {"detail": "Permission assigned to role", "data": serializer.data},
                    status=status.HTTP_201_CREATED
                )
            except IntegrityError:
                logger.warning(f"Duplicate permission assignment attempt: role={request.data.get('role')}, permission={request.data.get('permission')}")
                return Response(
                    {"detail": "This permission is already assigned to this role"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AssignRoleToUser(APIView):
    """Assign a role to a user. Requires 'assign_role' permission or superuser."""
    permission_classes = [IsAdminOrHasPermission]
    required_permission = "assign_role"

    def post(self, request):
        
        serializer = UserRoleSerializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save()
                user_id = serializer.data.get('user')
                role_id = serializer.data.get('role')
                audit_logger.info(f"Role assigned to user: user_id={user_id}, role_id={role_id}, assigned_by={request.user.id}")
                return Response(
                    {"detail": "Role assigned to user", "data": serializer.data},
                    status=status.HTTP_201_CREATED
                )
            except IntegrityError:
                logger.warning(f"Duplicate role assignment attempt: user={request.data.get('user')}, role={request.data.get('role')}")
                return Response(
                    {"detail": "This role is already assigned to this user"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserList(APIView):
    """List all users. Requires 'view_users' permission or superuser."""
    permission_classes = [IsAdminOrHasPermission]
    required_permission = "view_users"

    def get(self, request):
        
        users = User.objects.prefetch_related("user_roles__role").all().order_by("id")
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class RoleList(APIView):
    """List all roles."""
    permission_classes = [IsAdmin]

    def get(self, request):
        roles = Role.objects.all().order_by("created_at")
        serializer = RoleSerializer(roles, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class PermissionList(APIView):
    """List all permissions."""
    permission_classes = [IsAdmin]

    def get(self, request):
        permissions = Permission.objects.all().order_by("created_at")
        serializer = PermissionSerializer(permissions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class StaffManagementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Owners to manage their staff (Sales Executives).
    Automatically links created staff to the Owner (request.user).
    """
    # serializer_class = UserMinimalSerializer
    permission_classes = [IsAuthenticated] # Allowed for authenticated users (Owners), filtered by queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return StaffCreateSerializer
        if self.action in ['update', 'partial_update']:
            return UserSerializer
        return UserMinimalSerializer

    def get_queryset(self):
        # Owners only see their own staff (children)
        return User.objects.filter(parent=self.request.user)

    def perform_create(self, serializer):
        # Permission Check
        if not self.request.user.is_superuser:
            from apps.users.utils import has_permission
            if not has_permission(self.request.user, 'manage_users'):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("You do not have permission to manage users.")

        # Check Staff Limit based on Subscription
        user = self.request.user
        if hasattr(user, 'subscription') and user.subscription.is_active():
            plan = user.subscription.plan
            max_staff = plan.max_staff_users
            
            # 0 means unlimited
            if max_staff > 0:
                current_staff_count = User.objects.filter(parent=user, is_active=True).count()
                if current_staff_count >= max_staff:
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError(
                        {"detail": f"You have reached the maximum number of staff members ({max_staff}) allowed for your current plan ({plan.name}). Please upgrade to add more staff."}
                    )

        # Automatically set parent to current user (Owner)
        created_user = serializer.save(parent=self.request.user)
        
        # Assign 'SALES_EXECUTIVE' role
        try:
            role = Role.objects.get(name="SALES_EXECUTIVE")
            UserRole.objects.create(user=created_user, role=role)
        except Role.DoesNotExist:
            logger.error("SALES_EXECUTIVE role not found")

        except Role.DoesNotExist:
            logger.error("SALES_EXECUTIVE role not found")

class RolePermissionMatrix(APIView):
    """
    Manage the matrix of roles and their permissions.
    GET: Returns { "ROLE_NAME": { "permission_code": true/false } }
    POST: Toggle a permission for a role.
    """
    permission_classes = [IsAdminOrHasPermission]
    required_permission = "manage_settings"

    def get(self, request):
        
        roles = Role.objects.exclude(name='SUPERADMIN') # Superadmin has all, no need to edit ideally, or include if needed
        # Or just all roles:
        roles = Role.objects.all()
        
        matrix = {}
        for role in roles:
            # Get all permissions for this role
            role_perms = RolePermission.objects.filter(role=role).values_list('permission__code', flat=True)
            
            # Convert to dict for easy frontend lookup
            # We can return just the list of enabled codes, frontend can map against master list
            matrix[role.name] = list(role_perms)
            
        return Response(matrix, status=status.HTTP_200_OK)

    def post(self, request):
        
        role_name = request.data.get('role')
        perm_code = request.data.get('permission')
        enabled = request.data.get('enabled')
        
        if not all([role_name, perm_code, enabled is not None]):
             return Response({"detail": "Missing role, permission or enabled status"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            role = Role.objects.get(name=role_name)
            permission = Permission.objects.get(code=perm_code)
        except (Role.DoesNotExist, Permission.DoesNotExist):
            return Response({"detail": "Role or Permission not found"}, status=status.HTTP_404_NOT_FOUND)

        if enabled:
            RolePermission.objects.get_or_create(role=role, permission=permission)
            audit_logger.info(f"Permission granted: role={role.name}, permission={permission.code}, user={request.user.id}")
        else:
            RolePermission.objects.filter(role=role, permission=permission).delete()
            audit_logger.info(f"Permission revoked: role={role.name}, permission={permission.code}, user={request.user.id}")
            
        return Response({"detail": "Permission updated"}, status=status.HTTP_200_OK)
