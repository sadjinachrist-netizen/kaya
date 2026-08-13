from rest_framework import serializers

from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    event_label = serializers.CharField(source="get_event_type_display", read_only=True)

    class Meta:
        model = Notification
        fields = ["id", "event_type", "event_label", "subject", "message",
                  "channel", "object_type", "object_id", "is_read", "read_at", "sent_at"]
        read_only_fields = fields


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    event_label = serializers.CharField(source="get_event_type_display", read_only=True)

    class Meta:
        model = NotificationPreference
        fields = ["id", "event_type", "event_label", "in_app", "by_email"]