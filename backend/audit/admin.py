from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "actor", "action", "object_type", "object_label", "ip_address"]
    list_filter = ["action", "object_type", "timestamp"]
    search_fields = ["object_type", "object_id", "object_label", "detail", "actor__username"]
    date_hierarchy = "timestamp"
    ordering = ["-timestamp"]

    # Journal en lecture seule, y compris pour un superutilisateur
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [champ.name for champ in self.model._meta.fields]