from django.contrib import admin

from .models import Permission, Role


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ["code", "module", "label"]
    list_filter = ["module"]
    search_fields = ["code", "label"]
    ordering = ["module", "code"]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["label", "code", "requires_mfa", "nb_permissions", "nb_utilisateurs"]
    list_filter = ["requires_mfa"]
    search_fields = ["code", "label"]
    filter_horizontal = ["permissions", "users"]

    @admin.display(description="Permissions")
    def nb_permissions(self, obj):
        return obj.permissions.count()

    @admin.display(description="Utilisateurs")
    def nb_utilisateurs(self, obj):
        return obj.users.count()