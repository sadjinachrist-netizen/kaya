from django.contrib import admin

from .models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["recipient", "event_type", "subject", "channel", "is_read", "sent_at"]
    list_filter = ["event_type", "channel", "is_read"]
    search_fields = ["subject", "message", "recipient__username"]
    date_hierarchy = "sent_at"


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ["user", "event_type", "in_app", "by_email"]
    list_filter = ["event_type", "in_app", "by_email"]