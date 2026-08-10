from django.contrib import admin

from .models import Permission, Role, RolePermission


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ["code", "module", "label"]
    list_filter = ["module"]
    search_fields = ["code", "label"]
    ordering = ["module", "code"]


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 0
    autocomplete_fields = ["permission"]
    verbose_name = "permission attribuee"
    verbose_name_plural = "permissions attribuees"


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["label", "code", "requires_mfa", "nb_permissions", "nb_utilisateurs"]
    list_filter = ["requires_mfa"]
    search_fields = ["code", "label"]
    filter_horizontal = ["users"]
    inlines = [RolePermissionInline]

    @admin.display(description="Permissions")
    def nb_permissions(self, obj):
        return obj.grants.count()

    @admin.display(description="Utilisateurs")
    def nb_utilisateurs(self, obj):
        return obj.users.count()