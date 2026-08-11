"""Capture automatique des ecritures en base dans le journal d'audit."""
from django.apps import apps
from django.contrib.admin import action
from django.db.models.signals import post_delete, post_save, pre_save

from .context import audit_actif, requete_courante, utilisateur_courant
from .models import AuditLog

# Modeles dont chaque ecriture est tracee
MODELES_AUDITES = [
    "accounts.User",
    "authorization.Role",
    "authorization.Permission",
    "authorization.RolePermission",
    "projects.Project",
    "projects.InterventionSite",
    "projects.TeamMember",
    "projects.Amendment",
]

# Jamais journalises : secrets ou bruit sans valeur
CHAMPS_EXCLUS = {"password", "last_login", "failed_login_attempts"}


def _serialiser(instance):
    donnees = {}
    for champ in instance._meta.fields:
        if champ.name in CHAMPS_EXCLUS:
            continue
        valeur = getattr(instance, champ.attname, None)
        donnees[champ.name] = None if valeur is None else str(valeur)
    return donnees


def _ip_du_client(request):
    if request is None:
        return None
    transmis = request.META.get("HTTP_X_FORWARDED_FOR")
    if transmis:
        return transmis.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _ecrire(action, instance, old_value=None, new_value=None):
     if not audit_actif():
        return
     request = requete_courante()
     AuditLog.objects.create(
        actor=utilisateur_courant(),
        action=action,
        object_type=instance.__class__.__name__,
        object_id=str(instance.pk or ""),
        object_label=str(instance)[:255],
        old_value=old_value,
        new_value=new_value,
        ip_address=_ip_du_client(request),
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:255] if request else ""),
    )


def avant_enregistrement(sender, instance, **kwargs):
    """Memorise l'etat en base avant modification."""
    if kwargs.get("raw") or instance.pk is None:
        instance._audit_ancien = None
        return
    ancien = sender.objects.filter(pk=instance.pk).first()
    instance._audit_ancien = _serialiser(ancien) if ancien else None


def apres_enregistrement(sender, instance, created, **kwargs):
    if kwargs.get("raw"):
        return
    nouveau = _serialiser(instance)
    if created:
        _ecrire(AuditLog.Action.CREATION, instance, new_value=nouveau)
        return

    ancien = getattr(instance, "_audit_ancien", None) or {}
    modifies = {c: v for c, v in nouveau.items() if ancien.get(c) != v}
    if not modifies:
        return  # aucun changement reel, on ne pollue pas le journal
    _ecrire(
        AuditLog.Action.MODIFICATION,
        instance,
        old_value={c: ancien.get(c) for c in modifies},
        new_value=modifies,
    )


def apres_suppression(sender, instance, **kwargs):
    _ecrire(AuditLog.Action.SUPPRESSION, instance, old_value=_serialiser(instance))


def connecter():
    for chemin in MODELES_AUDITES:
        modele = apps.get_model(chemin)
        pre_save.connect(avant_enregistrement, sender=modele, dispatch_uid=f"audit_pre_{chemin}")
        post_save.connect(apres_enregistrement, sender=modele, dispatch_uid=f"audit_post_{chemin}")
        post_delete.connect(apres_suppression, sender=modele, dispatch_uid=f"audit_del_{chemin}")