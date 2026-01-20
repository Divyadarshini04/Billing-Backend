from django.db import models
from apps.auth_app.models import User
from django.db.models import UniqueConstraint, Index

class Role(models.Model):
    """Role model with metadata tracking and unique constraint."""
    name = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            Index(fields=["name"]),
        ]

    def __str__(self):
        return self.name

class Permission(models.Model):
    """Permission model with metadata tracking and unique constraint."""
    code = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            Index(fields=["code"]),
        ]

    def __str__(self):
        return self.code

class RolePermission(models.Model):
    """Through model for Role-Permission relationships with audit trail."""
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="permission_roles")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("role", "permission")
        constraints = [
            UniqueConstraint(fields=["role", "permission"], name="unique_role_permission")
        ]
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role.name} -> {self.permission.code}"

class UserRole(models.Model):
    """Through model for User-Role relationships with audit trail."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_users")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "role")
        constraints = [
            UniqueConstraint(fields=["user", "role"], name="unique_user_role")
        ]
        indexes = [
            Index(fields=["user", "created_at"]),
            Index(fields=["role", "created_at"]),
        ]
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user.phone} -> {self.role.name}"
