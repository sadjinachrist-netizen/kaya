from django.contrib import admin

from .models import (
    Consent,
    DuplicateCandidate,
    Household,
    HouseholdProject,
    Person,
    Vulnerability,
)


class PersonInline(admin.TabularInline):
    model = Person
    extra = 0
    fields = ["first_name", "last_name", "sex", "birth_date", "estimated_age",
              "relation_to_head", "is_head", "is_enrolled", "has_disability"]


class ConsentInline(admin.StackedInline):
    model = Consent
    extra = 0
    can_delete = False


class HouseholdProjectInline(admin.TabularInline):
    model = HouseholdProject
    extra = 0
    autocomplete_fields = ["project"]


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ["code", "head_name", "size", "zone", "residence_status",
                    "validation_status", "registered_by", "registered_at"]
    list_filter = ["validation_status", "residence_status", "zone__level", "registered_at"]
    search_fields = ["code", "head_name", "zone__name"]
    autocomplete_fields = ["zone", "registered_by"]
    filter_horizontal = ["vulnerabilities"]
    date_hierarchy = "registered_at"
    readonly_fields = ["client_uuid"]
    inlines = [PersonInline, ConsentInline, HouseholdProjectInline]


@admin.register(Vulnerability)
class VulnerabilityAdmin(admin.ModelAdmin):
    list_display = ["label", "code", "weight", "is_active"]
    search_fields = ["code", "label"]


@admin.register(DuplicateCandidate)
class DuplicateCandidateAdmin(admin.ModelAdmin):
    list_display = ["household_a", "household_b", "score", "status", "reviewed_by", "reviewed_at"]
    list_filter = ["status"]
    search_fields = ["household_a__code", "household_b__code",
                     "household_a__head_name", "household_b__head_name"]
    autocomplete_fields = ["household_a", "household_b", "reviewed_by"]
    readonly_fields = ["score"]