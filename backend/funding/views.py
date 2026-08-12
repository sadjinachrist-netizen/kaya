"""API des financements et du budget."""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from authorization.permissions import PermissionMetier

from .models import BudgetLine, Expense, Grant, GrantProject, Installment, ReportDeadline
from .serializers import (
    BudgetLineSerializer,
    ExpenseSerializer,
    GrantDetailSerializer,
    GrantListSerializer,
    GrantProjectSerializer,
    InstallmentSerializer,
    ReportDeadlineSerializer,
)
from .services import financements_accessibles


class GrantViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, PermissionMetier]
    permission_codes = {
        "list": "financement.consulter",
        "retrieve": "financement.consulter",
        "create": "financement.creer",
        "update": "financement.modifier",
        "partial_update": "financement.modifier",
        "destroy": "financement.modifier",
        "echeances_proches": "financement.consulter",
    }
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["contract_number", "title", "donor__name", "donor__acronym"]
    ordering_fields = ["contract_number", "signature_date", "amount", "eligibility_end"]
    ordering = ["-signature_date"]

    def get_queryset(self):
        requete = financements_accessibles(self.request.user).select_related(
            "donor", "currency"
        ).prefetch_related("project_links__project", "budget_lines", "deadlines", "installments")
        for parametre, champ in (("statut", "status"), ("bailleur", "donor_id")):
            valeur = self.request.query_params.get(parametre)
            if valeur:
                requete = requete.filter(**{champ: valeur})
        return requete

    def get_serializer_class(self):
        return GrantListSerializer if self.action == "list" else GrantDetailSerializer

    @action(detail=False, methods=["get"], url_path="echeances-proches")
    def echeances_proches(self, request):
        """Echeances de rapportage a moins de 30 jours, toutes conventions."""
        echeances = ReportDeadline.objects.filter(
            grant__in=self.get_queryset(),
            status__in=[ReportDeadline.Status.A_FAIRE, ReportDeadline.Status.EN_COURS],
            due_date__lte=timezone.localdate() + timezone.timedelta(days=30),
        ).select_related("grant__donor").order_by("due_date")
        return Response(ReportDeadlineSerializer(echeances, many=True).data)


class GrantProjectViewSet(viewsets.ModelViewSet):
    serializer_class = GrantProjectSerializer
    permission_classes = [IsAuthenticated, PermissionMetier]
    permission_codes = {
        "list": "financement.consulter",
        "retrieve": "financement.consulter",
        "default": "financement.modifier",
    }

    def get_queryset(self):
        return GrantProject.objects.filter(
            grant__in=financements_accessibles(self.request.user)
        ).select_related("grant", "project")


class BudgetLineViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetLineSerializer
    permission_classes = [IsAuthenticated, PermissionMetier]
    permission_codes = {
        "list": "budget.consulter",
        "retrieve": "budget.consulter",
        "default": "budget.gerer",
    }
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["code", "label"]
    ordering = ["code"]

    def get_queryset(self):
        requete = BudgetLine.objects.filter(
            grant__in=financements_accessibles(self.request.user)
        ).select_related("grant").prefetch_related("expenses")
        financement = self.request.query_params.get("financement")
        if financement:
            requete = requete.filter(grant_id=financement)
        parent = self.request.query_params.get("parent")
        if parent == "racines":
            requete = requete.filter(parent__isnull=True)
        elif parent:
            requete = requete.filter(parent_id=parent)
        return requete


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated, PermissionMetier]
    permission_codes = {
        "list": "budget.consulter",
        "retrieve": "budget.consulter",
        "create": "depense.saisir",
        "update": "depense.saisir",
        "partial_update": "depense.saisir",
        "destroy": "depense.saisir",
        "valider": "depense.valider",
        "rejeter": "depense.valider",
    }
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["label"]
    ordering_fields = ["expense_date", "amount", "created_at"]
    ordering = ["-expense_date"]

    def get_queryset(self):
        requete = Expense.objects.filter(
            budget_line__grant__in=financements_accessibles(self.request.user)
        ).select_related("budget_line", "project", "currency", "entered_by")
        for parametre, champ in (("statut", "status"), ("projet", "project_id"),
                                 ("ligne", "budget_line_id")):
            valeur = self.request.query_params.get(parametre)
            if valeur:
                requete = requete.filter(**{champ: valeur})
        return requete

    def perform_create(self, serializer):
        serializer.save(entered_by=self.request.user)

    def _statuer(self, request, nouveau_statut):
        depense = self.get_object()
        if depense.status != Expense.Status.SAISIE:
            raise ValidationError({"statut": "Cette depense a deja ete statuee."})
        depense.status = nouveau_statut
        depense.validated_by = request.user
        depense.save(update_fields=["status", "validated_by"])

        corps = ExpenseSerializer(depense).data
        ligne = depense.budget_line
        if nouveau_statut == Expense.Status.VALIDEE and ligne.est_depassee:
            corps["alerte"] = (
                f"Ligne budgetaire depassee : {ligne.montant_depense} depenses "
                f"pour {ligne.budgeted_amount} budgetes."
            )
        return Response(corps)

    @action(detail=True, methods=["post"])
    def valider(self, request, pk=None):
        return self._statuer(request, Expense.Status.VALIDEE)

    @action(detail=True, methods=["post"])
    def rejeter(self, request, pk=None):
        return self._statuer(request, Expense.Status.REJETEE)


class ReportDeadlineViewSet(viewsets.ModelViewSet):
    serializer_class = ReportDeadlineSerializer
    permission_classes = [IsAuthenticated, PermissionMetier]
    permission_codes = {
        "list": "financement.consulter",
        "retrieve": "financement.consulter",
        "default": "financement.modifier",
    }
    ordering = ["due_date"]

    def get_queryset(self):
        requete = ReportDeadline.objects.filter(
            grant__in=financements_accessibles(self.request.user)
        ).select_related("grant")
        financement = self.request.query_params.get("financement")
        return requete.filter(grant_id=financement) if financement else requete


class InstallmentViewSet(viewsets.ModelViewSet):
    serializer_class = InstallmentSerializer
    permission_classes = [IsAuthenticated, PermissionMetier]
    permission_codes = {
        "list": "financement.consulter",
        "retrieve": "financement.consulter",
        "default": "financement.modifier",
    }
    ordering = ["expected_date"]

    def get_queryset(self):
        return Installment.objects.filter(
            grant__in=financements_accessibles(self.request.user)
        ).select_related("grant")