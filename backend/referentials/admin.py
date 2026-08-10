from django.contrib import admin

from .models import Currency, Donor, ExchangeRate, Organization, Sector, Zone


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "acronym", "email", "phone"]

    # Instance unique : ni ajout ni suppression
    def has_add_permission(self, request):
        return not Organization.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ["name", "level", "parent", "code", "is_active"]
    list_filter = ["level", "is_active"]
    search_fields = ["code", "name"]
    autocomplete_fields = ["parent"]
    ordering = ["level", "name"]


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ["label", "code", "parent", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "label"]
    autocomplete_fields = ["parent"]


@admin.register(Donor)
class DonorAdmin(admin.ModelAdmin):
    list_display = ["name", "acronym", "type", "country", "is_active"]
    list_filter = ["type", "is_active"]
    search_fields = ["name", "acronym"]


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "symbol", "is_base"]
    search_fields = ["code", "name"]


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ["currency", "base_currency", "rate", "effective_date"]
    list_filter = ["currency", "base_currency"]
    date_hierarchy = "effective_date"
    autocomplete_fields = ["currency", "base_currency"]