from django.contrib import admin

from .models import Activity, ActivityParticipation, Attachment


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0
    readonly_fields = ["mime_type", "size", "uploaded_at"]


class ParticipationInline(admin.TabularInline):
    model = ActivityParticipation
    extra = 0
    autocomplete_fields = ["household"]


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ["code", "type", "project", "activity_date", "zone", "status", "agent"]
    list_filter = ["status", "type", "project", "activity_date"]
    search_fields = ["code", "description", "results"]
    date_hierarchy = "activity_date"
    autocomplete_fields = ["project", "zone", "agent"]
    readonly_fields = ["code", "submitted_at", "validated_by", "validated_at", "created_at"]
    inlines = [AttachmentInline, ParticipationInline]