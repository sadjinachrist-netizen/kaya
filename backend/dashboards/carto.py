"""Donnees geographiques pour la cartographie.

Regle de protection : aucun point individuel de menage n'est expose. La
couverture beneficiaire est agregee a la prefecture, conformement au §4.10
qui prevoit une carte de densite et non une carte de personnes.
"""
from collections import defaultdict

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from activities.models import Activity
from authorization.permissions import PermissionMetier
from authorization.scopes import projets_accessibles
from beneficiaries.models import Household
from projects.models import InterventionSite
from referentials.models import Zone


def _ancetre(zone, niveau):
    """Remonte la hierarchie jusqu'au niveau demande."""
    while zone is not None and zone.level != niveau:
        zone = zone.parent
    return zone


def _zone_situee(zone):
    """Premiere zone geolocalisee en remontant : village, canton, prefecture, region.

    Evite une carte vide lorsque le referentiel n'est pas encore complet.
    """
    while zone is not None and zone.latitude is None:
        zone = zone.parent
    return zone


class VueCarto(APIView):
    permission_classes = [IsAuthenticated, PermissionMetier]
    permission_codes = {"default": "projet.consulter"}


class SitesCartoView(VueCarto):
    """Sites d'intervention des projets accessibles, avec leurs coordonnees."""

    def get(self, request):
        sites = InterventionSite.objects.filter(
            project__in=projets_accessibles(request.user)
        ).select_related("project", "zone__parent__parent__parent")

        points = []
        for site in sites:
            situee = _zone_situee(site.zone)
            latitude = site.latitude or (situee.latitude if situee else None)
            longitude = site.longitude or (situee.longitude if situee else None)
            if latitude is None or longitude is None:
                continue
            points.append({
                "id": site.id,
                "projet": site.project.code,
                "projet_id": site.project_id,
                "titre": site.project.title,
                "statut": site.project.get_status_display(),
                "localite": site.zone.name,
                "latitude": float(latitude),
                "longitude": float(longitude),
                "population_cible": site.target_population,
            })
        return Response(points)


class ActivitesCartoView(VueCarto):
    """Points GPS des activites validees — controle de presence terrain."""

    permission_codes = {"default": "activite.consulter"}

    def get(self, request):
        activites = Activity.objects.filter(
            project__in=projets_accessibles(request.user),
            status=Activity.Status.VALIDEE,
            latitude__isnull=False,
            longitude__isnull=False,
        ).select_related("project", "zone", "agent")

        type_demande = request.query_params.get("type")
        if type_demande:
            activites = activites.filter(type=type_demande)

        return Response([
            {
                "id": a.id,
                "code": a.code,
                "type": a.get_type_display(),
                "date": a.activity_date,
                "projet": a.project.code,
                "localite": a.zone.name,
                "agent": a.agent.full_name,
                "latitude": float(a.latitude),
                "longitude": float(a.longitude),
            }
            for a in activites[:500]
        ])


class CouvertureCartoView(VueCarto):
    """Densite de menages par prefecture. Effectifs agreges, jamais nominatifs."""

    permission_codes = {"default": "beneficiaire.consulter"}

    def get(self, request):
        menages = Household.objects.filter(
            project_links__project__in=projets_accessibles(request.user)
        ).exclude(
            validation_status=Household.ValidationStatus.DOUBLON
        ).select_related("zone__parent__parent__parent").distinct()

        compte = defaultdict(int)
        for menage in menages:
            unite = _ancetre(menage.zone, Zone.Level.PREFECTURE) or _zone_situee(menage.zone)
            if unite is not None and unite.latitude is not None:
                compte[unite] += 1

        return Response([
            {
                "prefecture": unite.name,
                "chemin": unite.full_path,
                "menages": total,
                "latitude": float(unite.latitude),
                "longitude": float(unite.longitude),
            }
            for unite, total in sorted(compte.items(), key=lambda c: -c[1])
        ])