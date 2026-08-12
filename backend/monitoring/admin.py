from django.contrib import admin

from .models import Indicator, IndicatorDisaggregation, IndicatorReading, LogFrameElement


class DisaggregationInline(admin.TabularInline):
    model = IndicatorDisaggregation
    extra = 0


class IndicatorInline(admin.TabularInline):
    model = Indicator
    extra = 0
    fields = ["code", "title", "unit", "baseline", "target", "computation_mode"]


@admin.register(LogFrameElement)
class LogFrameElementAdmin(admin.ModelAdmin):
    list_display = ["code", "type", "title", "project", "parent", "position"]
    list_filter = ["type", "project"]
    search_fields = ["code", "title"]
    autocomplete_fields = ["project", "parent"]
    inlines = [IndicatorInline]


@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ["code", "title", "unit", "baseline", "target",
                    "valeur_atteinte", "taux_atteinte", "statut_atteinte", "computation_mode"]
    list_filter = ["unit", "frequency", "computation_mode", "element__project"]
    search_fields = ["code", "title"]
    autocomplete_fields = ["element", "owner"]
    inlines = [DisaggregationInline]


@admin.register(IndicatorReading)
class IndicatorReadingAdmin(admin.ModelAdmin):
    list_display = ["indicator", "period_start", "period_end", "achieved_value",
                    "taux_atteinte", "status", "entered_by"]
    list_filter = ["status", "period_end"]
    autocomplete_fields = ["indicator", "entered_by", "validated_by"]
    date_hierarchy = "period_end"