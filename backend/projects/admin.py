from django.contrib import admin

from .models import Amendment, InterventionSite, Project, TeamMember


class InterventionSiteInline(admin.TabularInline):
    model = InterventionSite
    extra = 0
    autocomplete_fields = ["zone"]


class TeamMemberInline(admin.TabularInline):
    model = TeamMember
    extra = 0
    autocomplete_fields = ["user"]


class AmendmentInline(admin.TabularInline):
    model = Amendment
    extra = 0
    readonly_fields = ["created_by", "created_at"]


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["code", "title", "status", "manager", "start_date", "end_date", "nb_sites"]
    list_filter = ["status", "sectors", "start_date"]
    search_fields = ["code", "title", "description"]
    autocomplete_fields = ["manager"]
    filter_horizontal = ["sectors"]
    date_hierarchy = "start_date"
    readonly_fields = ["progress_rate", "created_at", "updated_at"]
    inlines = [InterventionSiteInline, TeamMemberInline, AmendmentInline]

    @admin.display(description="Sites")
    def nb_sites(self, obj):
        return obj.sites.count()


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ["user", "project", "project_role", "start_date", "end_date", "is_active"]
    list_filter = ["project_role", "project"]
    autocomplete_fields = ["user", "project"]

    @admin.display(boolean=True, description="Active")
    def is_active(self, obj):
        return obj.is_active