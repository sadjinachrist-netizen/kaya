"""API du cadre logique et des indicateurs."""
from django.db.models import Count
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from authorization.permissions import PermissionMetier
from authorization.scopes import projets_accessibles

from .models import Indicator, IndicatorReading, LogFrameElement
from .serializers import (
    IndicatorDetailSerializer,
    IndicatorListSerializer,
    IndicatorReadingSerializer,
    LogFrameArbreSerializer,
    LogFrameElementSerializer,
)


class LogFrameElementViewSet(viewsets.ModelViewSet):
    serializer_class = LogFrameElementSerializer
    permission_classes = [IsAuthenticated, PermissionMetier]
    permission_codes = {
        "list": "indicateur.consulter",
        "retrieve": "indicateur.consulter",
        "arbre": "indicateur.consulter",
        "default": "cadre_logique.gerer",
    }
    ordering = ["position", "code"]

    def get_queryset(self):
        requete = LogFrameElement.objects.filter(
            project__in=projets_accessibles(self.request.user)
        ).select_related("project", "parent").prefetch_related("indicators")
        projet = self.request.query_params.get("projet")
        if projet:
            requete = requete.filter(project_id=projet)
        niveau = self.request.query_params.get("niveau")
        if niveau:
            requete = requete.filter(type=niveau)
        return requete

    @action(detail=False, methods=["get"])
    def arbre(self, request):
        """Cadre logique complet d'un projet, sous forme d'arborescence."""
        projet = request.query_params.get("projet")
        if not projet:
            raise ValidationError({"projet": "Parametre obligatoire."})
        racines = self.get_queryset().filter(
            project_id=projet, type=LogFrameElement.Type.OBJECTIF_GENERAL
        )
        return Response(LogFrameArbreSerializer(racines, many=True).data)


class IndicatorViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, PermissionMetier]
    permission_codes = {
        "list": "indicateur.consulter",
        "retrieve": "indicateur.consulter",
        "calculer": "indicateur.consulter",
        "consolides": "indicateur.consolider",
        "default": "indicateur.definir",
    }
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["code", "title", "definition"]
    ordering = ["code"]

    def get_queryset(self):
        requete = Indicator.objects.filter(
            element__project__in=projets_accessibles(self.request.user)
        ).select_related("element__project", "owner").prefetch_related(
            "disaggregations", "readings"
        )
        projet = self.request.query_params.get("projet")
        if projet:
            requete = requete.filter(element__project_id=projet)
        statut = self.request.query_params.get("statut")
        if statut:
            identifiants = [i.id for i in requete if i.statut_atteinte == statut]
            requete = requete.filter(id__in=identifiants)
        return requete

    def get_serializer_class(self):
        return IndicatorListSerializer if self.action == "list" else IndicatorDetailSerializer

    @action(detail=True, methods=["get"])
    def calculer(self, request, pk=None):
        """Valeur proposee par le systeme, avant validation humaine."""
        indicateur = self.get_object()
        valeur = indicateur.calculer()
        return Response({
            "indicateur": indicateur.code,
            "mode": indicateur.computation_mode,
            "source": indicateur.computation_source or None,
            "valeur_proposee": None if valeur is None else str(valeur),
            "cible": str(indicateur.target),
            "message": (
                "Indicateur saisi manuellement : aucune valeur calculable."
                if valeur is None else
                "Valeur calculee depuis les donnees de la plateforme."
            ),
        })

    @action(detail=False, methods=["get"])
    def consolides(self, request):
        """Vue institutionnelle : indicateurs agreges par unite de mesure."""
        indicateurs = self.get_queryset()
        par_statut = {"atteint": 0, "en_cours": 0, "en_retard": 0}
        for indicateur in indicateurs:
            par_statut[indicateur.statut_atteinte] += 1
        return Response({
            "nb_indicateurs": indicateurs.count(),
            "repartition": par_statut,
            "par_projet": list(
                indicateurs.values("element__project__code", "element__project__title")
                .annotate(nb=Count("id"))
                .order_by("element__project__code")
            ),
        })


class IndicatorReadingViewSet(viewsets.ModelViewSet):
    serializer_class = IndicatorReadingSerializer
    permission_classes = [IsAuthenticated, PermissionMetier]
    permission_codes = {
        "list": "indicateur.consulter",
        "retrieve": "indicateur.consulter",
        "valider": "indicateur.valider",
        "default": "indicateur.relever",
    }
    ordering = ["-period_end"]

    def get_queryset(self):
        requete = IndicatorReading.objects.filter(
            indicator__element__project__in=projets_accessibles(self.request.user)
        ).select_related("indicator", "entered_by", "validated_by")
        indicateur = self.request.query_params.get("indicateur")
        if indicateur:
            requete = requete.filter(indicator_id=indicateur)
        return requete

    def perform_create(self, serializer):
        serializer.save(entered_by=self.request.user)

    @action(detail=True, methods=["post"])
    def valider(self, request, pk=None):
        releve = self.get_object()
        if releve.status == IndicatorReading.Status.VALIDE:
            raise ValidationError({"statut": "Ce releve est deja valide."})
        releve.status = IndicatorReading.Status.VALIDE
        releve.validated_by = request.user
        try:
            releve.full_clean(exclude=["entered_by"])
        except Exception as erreur:
            raise ValidationError(getattr(erreur, "message_dict", str(erreur)))
        releve.save(update_fields=["status", "validated_by"])

        corps = IndicatorReadingSerializer(releve).data
        if releve.indicator.taux_atteinte < 60:
            corps["alerte"] = (
                f"Taux d'atteinte de {releve.indicator.taux_atteinte} % — "
                f"le chef de projet et la Direction doivent etre informes."
            )
        return Response(corps)