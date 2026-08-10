from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["username"]
    list_display = ["username", "email", "full_name", "is_active", "mfa_enabled", "is_staff"]
    list_filter = ["is_active", "is_staff", "is_superuser", "mfa_enabled"]
    search_fields = ["username", "email", "first_name", "last_name", "phone"]

    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        ("Identite", {"fields": ("first_name", "last_name", "phone")}),
        ("Securite", {"fields": ("mfa_enabled", "failed_login_attempts", "locked_until")}),
        ("Droits", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "username", "password1", "password2"),
        }),
    )