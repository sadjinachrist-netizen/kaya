"""API des notifications de l'utilisateur connecte."""
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import EventType, Notification, NotificationPreference
from .serializers import NotificationPreferenceSerializer, NotificationSerializer


class NotificationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                          viewsets.GenericViewSet):
    """Un utilisateur n'accede qu'a ses propres notifications."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        requete = Notification.objects.filter(recipient=self.request.user)
        if self.request.query_params.get("non_lues") == "1":
            requete = requete.filter(is_read=False)
        return requete

    @action(detail=False, methods=["get"])
    def compteur(self, request):
        return Response({
            "non_lues": Notification.objects.filter(
                recipient=request.user, is_read=False
            ).count()
        })

    @action(detail=True, methods=["post"], url_path="marquer-lue")
    def marquer_lue(self, request, pk=None):
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at"])
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=["post"], url_path="tout-marquer-lu")
    def tout_marquer_lu(self, request):
        nombre = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True, read_at=timezone.now())
        return Response({"marquees": nombre})


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return NotificationPreference.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["get"])
    def disponibles(self, request):
        """Liste des evenements notifiables, avec la preference courante."""
        existantes = {
            p.event_type: p for p in self.get_queryset()
        }
        return Response([
            {
                "event_type": code,
                "event_label": libelle,
                "in_app": existantes[code].in_app if code in existantes else True,
                "by_email": existantes[code].by_email if code in existantes else False,
            }
            for code, libelle in EventType.choices
        ])