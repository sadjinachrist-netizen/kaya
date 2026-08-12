"""API des referentiels — lecture ouverte a tout utilisateur authentifie."""
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authorization.permissions import PermissionMetier

from .models import Currency, Donor, ExchangeRate, Organization, Sector, Zone
from .serializers import (
    CurrencySerializer,
    DonorSerializer,
    ExchangeRateSerializer,
    OrganizationSerializer,
    SectorSerializer,
    ZoneSerializer,
)


class ReferentielViewSet(viewsets.ReadOnlyModelViewSet):
    """Base commune : lecture seule, pagination desactivee.

    Les referentiels alimentent des listes deroulantes : les paginer
    obligerait le front a boucler pour obtenir 39 prefectures.
    """

    permission_classes = [IsAuthenticated]
    pagination_class = None
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]


class ZoneViewSet(ReferentielViewSet):
    serializer_class = ZoneSerializer
    search_fields = ["code", "name"]
    ordering_fields = ["name", "level"]

    def get_queryset(self):
        requete = Zone.objects.filter(is_active=True).select_related("parent")
        niveau = self.request.query_params.get("niveau")
        if niveau:
            requete = requete.filter(level=niveau)
        parent = self.request.query_params.get("parent")
        if parent:
            requete = requete.filter(parent_id=parent)
        return requete


class SectorViewSet(ReferentielViewSet):
    serializer_class = SectorSerializer
    search_fields = ["code", "label"]
    queryset = Sector.objects.filter(is_active=True)


class DonorViewSet(ReferentielViewSet):
    serializer_class = DonorSerializer
    search_fields = ["name", "acronym"]
    queryset = Donor.objects.filter(is_active=True)


class CurrencyViewSet(ReferentielViewSet):
    serializer_class = CurrencySerializer
    queryset = Currency.objects.all()


class ExchangeRateViewSet(ReferentielViewSet):
    serializer_class = ExchangeRateSerializer
    queryset = ExchangeRate.objects.select_related("currency", "base_currency")


class VulnerabiliteViewSet(ReferentielViewSet):
    """Expose les criteres de vulnerabilite, portes par le module beneficiaires."""

    search_fields = ["code", "label"]

    def get_queryset(self):
        from beneficiaries.models import Vulnerability

        return Vulnerability.objects.filter(is_active=True)

    def get_serializer_class(self):
        from beneficiaries.serializers import VulnerabilitySerializer

        return VulnerabilitySerializer


class OrganisationView(APIView):
    """Identite de l'ONG, utilisee dans les en-tetes et le portail."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(OrganizationSerializer(Organization.get_solo()).data)