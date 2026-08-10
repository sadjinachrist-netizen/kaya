"""Point d'entree unique pour ecrire dans le journal d'audit."""
from .models import AuditLog


def _ip_du_client(request):
    if request is None:
        return None
    transmis = request.META.get("HTTP_X_FORWARDED_FOR")
    if transmis:
        return transmis.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def journaliser(action, *, actor=None, obj=None, object_type=None, object_id=None,
                object_label="", old_value=None, new_value=None, detail="",
                request=None):
    """Ecrit une entree dans le journal d'audit.

    Peut recevoir directement une instance de modele via `obj`, ou bien
    le type et l'identifiant separement lorsque l'objet n'existe plus.
    """
    if obj is not None:
        object_type = object_type or obj.__class__.__name__
        object_id = object_id or str(obj.pk)
        object_label = object_label or str(obj)[:255]

    if actor is None and request is not None:
        utilisateur = getattr(request, "user", None)
        if utilisateur is not None and utilisateur.is_authenticated:
            actor = utilisateur

    return AuditLog.objects.create(
        actor=actor,
        action=action,
        object_type=object_type or "",
        object_id=str(object_id or ""),
        object_label=object_label,
        old_value=old_value,
        new_value=new_value,
        detail=detail[:255],
        ip_address=_ip_du_client(request),
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:255] if request else ""),
    )