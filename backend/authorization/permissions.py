"""Controle des permissions metier au niveau de l'API."""
from rest_framework.permissions import BasePermission

from audit.models import AuditLog
from audit.services import journaliser


class PermissionMetier(BasePermission):
    """Verifie que l'utilisateur detient la permission exigee par la vue.

    La vue declare un dictionnaire `permission_codes` associant chaque
    action a un code de permission. Un refus est systematiquement journalise.
    """

    message = "Vous ne disposez pas de la permission requise pour cette action."

    def has_permission(self, request, view):
        codes = getattr(view, "permission_codes", {})
        code = codes.get(getattr(view, "action", None)) or codes.get("default")
        if code is None:
            return True

        utilisateur = request.user
        if not utilisateur.is_authenticated:
            return False
        if utilisateur.has_permission(code):
            return True

        journaliser(
            AuditLog.Action.ACCES_REFUSE,
            actor=utilisateur,
            object_type=view.__class__.__name__,
            detail=f"Permission '{code}' refusee",
            request=request,
        )
        return False