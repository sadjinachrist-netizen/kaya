"""API des activites terrain."""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from authorization.permissions import PermissionMetier

from .models import Activity
from .serializers import (
    ActivityDetailSerializer,
    ActivityListSerializer,
    ActivityWriteSerializer,
    AttachmentSerializer,
    RejetSerializer,
)
from .services import activites_accessibles


class ActivityViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, PermissionMetier]
    permission_codes = {
        "list": "activite.consulter",
        "retrieve": "activite.consulter",
        "create": "activite.creer",
        "update": "activite.modifier",
        "partial_update": "activite.modifier",
        "destroy": "activite.modifier",
        "soumettre": "activite.creer",
        "corriger": "activite.modifier",
        "valider": "activite.valider",
        "rejeter": "activite.valider",
        "piece_jointe": "activite.modifier",
    }
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["code", "description", "results"]
    ordering_fields = ["activity_date", "created_at", "status"]
    ordering = ["-activity_date"]

    def get_queryset(self):
        requete = activites_accessibles(self.request.user).select_related(
            "project", "zone", "agent", "validated_by"
        ).prefetch_related("attachments", "participations__household")

        for parametre, champ in (("statut", "status"), ("projet", "project_id"),
                                 ("type", "type"), ("agent", "agent_id")):
            valeur = self.request.query_params.get(parametre)
            if valeur:
                requete = requete.filter(**{champ: valeur})
        return requete

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ActivityWriteSerializer
        if self.action == "list":
            return ActivityListSerializer
        return ActivityDetailSerializer

    # ------------------------------------------------------------ garde-fous
    def _verifier_proprietaire(self, activite):
        """Un agent ne modifie que ses propres saisies, non validees."""
        utilisateur = self.request.user
        if utilisateur.is_superuser:
            return
        if activite.agent_id != utilisateur.id:
            raise PermissionDenied("Vous ne pouvez modifier que vos propres saisies.")
        if not activite.est_modifiable:
            raise PermissionDenied(
                "Une activite soumise ou validee ne peut plus etre modifiee."
            )

    def perform_update(self, serializer):
        self._verifier_proprietaire(self.get_object())
        serializer.save()

    def perform_destroy(self, instance):
        self._verifier_proprietaire(instance)
        instance.delete()

    def _detail(self, activite):
        return Response(
            ActivityDetailSerializer(activite, context=self.get_serializer_context()).data
        )

    # ------------------------------------------------------------- workflow
    @action(detail=True, methods=["post"])
    def soumettre(self, request, pk=None):
        activite = self.get_object()
        if activite.agent_id != request.user.id and not request.user.is_superuser:
            raise PermissionDenied("Seul l'auteur peut soumettre sa saisie.")
        try:
            activite.soumettre(auteur=request.user)
        except DjangoValidationError as erreur:
            raise ValidationError(erreur.messages)
        return self._detail(activite)

    @action(detail=True, methods=["post"])
    def valider(self, request, pk=None):
        activite = self.get_object()
        if activite.agent_id == request.user.id and not request.user.is_superuser:
            raise PermissionDenied("Vous ne pouvez pas valider votre propre saisie.")
        try:
            activite.valider(auteur=request.user)
        except DjangoValidationError as erreur:
            raise ValidationError(erreur.messages)
        return self._detail(activite)

    @action(detail=True, methods=["post"])
    def rejeter(self, request, pk=None):
        activite = self.get_object()
        entree = RejetSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        try:
            activite.rejeter(auteur=request.user, motif=entree.validated_data["motif"])
        except DjangoValidationError as erreur:
            raise ValidationError(erreur.messages)
        return self._detail(activite)

    @action(detail=True, methods=["post"])
    def corriger(self, request, pk=None):
        activite = self.get_object()
        if activite.agent_id != request.user.id and not request.user.is_superuser:
            raise PermissionDenied("Seul l'auteur peut reprendre sa saisie.")
        try:
            activite.corriger()
        except DjangoValidationError as erreur:
            raise ValidationError(erreur.messages)
        return self._detail(activite)

    @action(detail=True, methods=["post"], url_path="piece-jointe",
            parser_classes=[MultiPartParser, FormParser])
    def piece_jointe(self, request, pk=None):
        activite = self.get_object()
        self._verifier_proprietaire(activite)
        entree = AttachmentSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        fichier = request.data["file"]
        piece = entree.save(
            activity=activite,
            mime_type=getattr(fichier, "content_type", ""),
            size=fichier.size,
        )
        try:
            piece.full_clean()
        except DjangoValidationError as erreur:
            piece.delete()
            raise ValidationError(erreur.message_dict)
        return Response(AttachmentSerializer(piece).data, status=status.HTTP_201_CREATED)