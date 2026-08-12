"""API des projets."""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from authorization.permissions import PermissionMetier
from authorization.scopes import projets_accessibles

from .models import Project
from .serializers import (
    ChangementStatutSerializer,
    ProjectListSerializer,
    ProjectSerializer,
)


class ProjectViewSet(viewsets.ModelViewSet):
    """Projets accessibles a l'utilisateur connecte.

    Le queryset est **toujours** restreint a la portee de l'utilisateur.
    Aucune action ne peut contourner ce filtrage.
    """

    permission_classes = [IsAuthenticated, PermissionMetier]
    permission_codes = {
        "list": "projet.consulter",
        "retrieve": "projet.consulter",
        "create": "projet.creer",
        "update": "projet.modifier",
        "partial_update": "projet.modifier",
        "destroy": "projet.modifier",
        "changer_statut": "projet.modifier",
    }
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["code", "title", "description"]
    ordering_fields = ["code", "title", "start_date", "end_date", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            projets_accessibles(self.request.user)
            .select_related("manager")
            .prefetch_related("sectors", "sites__zone", "members__user")
        )

    def get_serializer_class(self):
        return ProjectListSerializer if self.action == "list" else ProjectSerializer

    def perform_create(self, serializer):
        serializer.save(manager=self.request.user)

    @action(detail=True, methods=["post"], url_path="changer-statut")
    def changer_statut(self, request, pk=None):
        """Fait evoluer le projet dans son cycle de vie."""
        projet = self.get_object()
        entree = ChangementStatutSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        try:
            projet.changer_statut(
                entree.validated_data["statut"],
                auteur=request.user,
                motif=entree.validated_data.get("motif", ""),
            )
        except DjangoValidationError as erreur:
            raise ValidationError({"statut": erreur.messages})
        return Response(ProjectSerializer(projet).data, status=status.HTTP_200_OK)