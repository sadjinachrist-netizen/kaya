from django.contrib import admin

from .models import BudgetLine, Expense, Grant, GrantProject, Installment, ReportDeadline


class GrantProjectInline(admin.TabularInline):
    model = GrantProject
    extra = 0
    autocomplete_fields = ["project"]


class BudgetLineInline(admin.TabularInline):
    model = BudgetLine
    extra = 0
    fields = ["code", "label", "category", "budgeted_amount", "parent"]


class DeadlineInline(admin.TabularInline):
    model = ReportDeadline
    extra = 0


class InstallmentInline(admin.TabularInline):
    model = Installment
    extra = 0


@admin.register(Grant)
class GrantAdmin(admin.ModelAdmin):
    list_display = ["contract_number", "donor", "amount", "currency", "status",
                    "eligibility_end", "taux_consommation", "ecart_rythme"]
    list_filter = ["status", "donor", "currency"]
    search_fields = ["contract_number", "title", "donor__name"]
    autocomplete_fields = ["donor", "currency"]
    date_hierarchy = "eligibility_start"
    inlines = [GrantProjectInline, BudgetLineInline, DeadlineInline, InstallmentInline]


@admin.register(BudgetLine)
class BudgetLineAdmin(admin.ModelAdmin):
    list_display = ["code", "label", "grant", "category", "budgeted_amount",
                    "montant_depense", "taux_consommation", "est_depassee"]
    list_filter = ["category", "grant"]
    search_fields = ["code", "label"]
    autocomplete_fields = ["grant", "parent"]


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["label", "amount", "currency", "expense_date", "budget_line",
                    "project", "status", "entered_by"]
    list_filter = ["status", "currency", "expense_date"]
    search_fields = ["label"]
    autocomplete_fields = ["budget_line", "project", "currency", "entered_by"]
    date_hierarchy = "expense_date"