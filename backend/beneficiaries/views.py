"""API des beneficiaires."""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from authorization.permissions import PermissionMetier

from .models import DuplicateCandidate, Household
from .serializers import (
    DuplicateCandidateSerializer,
    HouseholdCreateSerializer,
    HouseholdDetailSerializer,
    HouseholdListSerializer,
)
from .services import arbitrer_doublon, menages_accessibles


class HouseholdViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, PermissionMetier]
    permission_codes = {
        "list": "beneficiaire.consulter",
        "retrieve": "beneficiaire.consulter",
        "create": "beneficiaire.creer",
        "update": "beneficiaire.modifier",
        "partial_update": "beneficiaire.modifier",
        "valider": "beneficiaire.valider",
    }
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["code", "head_name", "zone__name"]
    ordering_fields = ["code", "registered_at", "size"]
    ordering = ["-registered_at"]

    def get_queryset(self):
        requete = menages_accessibles(self.request.user).select_related(
            "zone", "registered_by", "consent"
        ).prefetch_related("members", "vulnerabilities")
        statut = self.request.query_params.get("statut")
        if statut:
            requete = requete.filter(validation_status=statut)
        return requete

    def get_serializer_class(self):
        if self.action == "create":
            return HouseholdCreateSerializer
        if self.action == "list":
            return HouseholdListSerializer
        return HouseholdDetailSerializer

    def create(self, request, *args, **kwargs):
        entree = self.get_serializer(data=request.data)
        entree.is_valid(raise_exception=True)
        try:
            menage = entree.save()
        except DjangoValidationError as erreur:
            raise ValidationError(erreur.messages)

        corps = HouseholdDetailSerializer(menage, context=self.get_serializer_context()).data
        corps["doublons_detectes"] = [
            {"menage": c.household_a.code, "score": str(c.score)}
            for c in getattr(entree, "_doublons", [])
        ]
        return Response(corps, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def valider(self, request, pk=None):
        menage = self.get_object()
        menage.validation_status = Household.ValidationStatus.VALIDE
        menage.save(update_fields=["validation_status"])
        return Response(
            HouseholdDetailSerializer(menage, context=self.get_serializer_context()).data
        )


class DuplicateCandidateViewSet(viewsets.ReadOnlyModelViewSet):
    """File d'arbitrage des doublons, reservee au superviseur."""

    serializer_class = DuplicateCandidateSerializer
    permission_classes = [IsAuthenticated, PermissionMetier]
    permission_codes = {"default": "doublon.arbitrer"}

    def get_queryset(self):
        menages = menages_accessibles(self.request.user)
        requete = DuplicateCandidate.objects.filter(
            household_a__in=menages, household_b__in=menages
        ).select_related("household_a__zone", "household_b__zone",
                         "household_a__registered_by", "household_b__registered_by")
        statut = self.request.query_params.get("statut", DuplicateCandidate.Status.A_ARBITRER)
        return requete.filter(status=statut) if statut else requete

    @action(detail=True, methods=["post"])
    def arbitrer(self, request, pk=None):
        candidat = self.get_object()
        confirme = request.data.get("confirme")
        if confirme is None:
            raise ValidationError({"confirme": "Champ obligatoire (true ou false)."})
        arbitrer_doublon(candidat, confirme=bool(confirme), arbitre_par=request.user)
        return Response(
            DuplicateCandidateSerializer(candidat, context=self.get_serializer_context()).data
        )