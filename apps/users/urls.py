from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    CreateRole,
    CreatePermission,
    AssignPermissionToRole,
    AssignRoleToUser,
    UserList,
    StaffManagementViewSet,
    RolePermissionMatrix
)

router = DefaultRouter()
router.register(r"staff", StaffManagementViewSet, basename="staff-management")

urlpatterns = [
    path("roles/create/", CreateRole.as_view(), name="create_role"),
    path("permissions/create/", CreatePermission.as_view(), name="create_permission"),
    path("roles/assign-permission/", AssignPermissionToRole.as_view(), name="assign_permission"),
    path("roles/matrix/", RolePermissionMatrix.as_view(), name="role_permission_matrix"),
    path("users/assign-role/", AssignRoleToUser.as_view(), name="assign_role"),
    path("list/", UserList.as_view(), name="user_list"),
    path("", include(router.urls)),
]
