"""Portail public — consultable sans authentification.

Aucune donnee personnelle n'est exposee. Les effectifs sont arrondis a la
baisse pour interdire toute reidentification sur de petits effectifs, et
seuls les projets explicitement marques publiables apparaissent.
"""
from django.db.models import Count
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from activities.models import Activity
from beneficiaries.models import Household, Person
from funding.models import Grant
from projects.models import Project
from referentials.models import Organization, Sector, Zone


def _arrondir(valeur, pas):
    """Arrondit a la baisse. 554 personnes deviennent 500."""
    return (valeur // pas) * pas if valeur >= pas else valeur


def _region(zone):
    """Remonte la hierarchie jusqu'a la region qui contient la zone."""
    while zone is not None and zone.level != Zone.Level.REGION:
        zone = zone.parent
    return zone


def _projets_publics():
    return Project.objects.filter(is_public=True)


class VuePublique(APIView):
    """Base des vues du portail : ni authentification, ni permission."""

    permission_classes = [AllowAny]
    authentication_classes = []


class OrganisationPubliqueView(VuePublique):
    def get(self, request):
        organisation = Organization.get_solo()
        return Response({
            "nom": organisation.name,
            "sigle": organisation.acronym,
            "adresse": organisation.address,
            "telephone": organisation.phone,
            "email": organisation.email,
            "mentions_legales": organisation.legal_notice,
        })


class ChiffresPublicsView(VuePublique):
    def get(self, request):
        projets = _projets_publics()

        menages = Household.objects.filter(
            project_links__project__in=projets
        ).exclude(
            validation_status=Household.ValidationStatus.DOUBLON
        ).distinct()

        personnes = Person.objects.filter(household__in=menages).count()

        zones = Zone.objects.filter(sites__project__in=projets).select_related(
            "parent__parent__parent"
        ).distinct()
        regions = {r.id for r in (_region(z) for z in zones) if r is not None}

        return Response({
            "projets_en_cours": projets.filter(status=Project.Status.EN_COURS).count(),
            "projets_total": projets.count(),
            "personnes_accompagnees": _arrondir(personnes, 100),
            "menages": _arrondir(menages.count(), 10),
            "localites": zones.count(),
            "regions": len(regions),
            "bailleurs": Grant.objects.filter(
                project_links__project__in=projets
            ).values("donor").distinct().count(),
            "activites_realisees": _arrondir(
                Activity.objects.filter(
                    project__in=projets, status=Activity.Status.VALIDEE
                ).count(),
                10,
            ),
        })


class ProjetsPublicsView(VuePublique):
    def get(self, request):
        projets = _projets_publics().prefetch_related(
            "sectors", "sites__zone__parent__parent__parent"
        ).order_by("-start_date")

        resultat = []
        for projet in projets:
            regions = sorted({
                r.name for r in (_region(s.zone) for s in projet.sites.all())
                if r is not None
            })
            resultat.append({
                "id": projet.id,
                "code": projet.code,
                "titre": projet.title,
                "description": projet.description,
                "secteurs": [s.label for s in projet.sectors.all()],
                "regions": regions,
                "debut": projet.start_date,
                "fin": projet.end_date,
                "statut": projet.get_status_display(),
                "en_cours": projet.status == Project.Status.EN_COURS,
                "beneficiaires_vises": projet.target_beneficiaries,
            })
        return Response(resultat)


class SecteursPublicsView(VuePublique):
    def get(self, request):
        secteurs = (
            Sector.objects.filter(projects__in=_projets_publics())
            .annotate(nb=Count("projects", distinct=True))
            .order_by("-nb", "label")
        )
        return Response([
            {"code": s.code, "label": s.label, "nb_projets": s.nb} for s in secteurs
        ])