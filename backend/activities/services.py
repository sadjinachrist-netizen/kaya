"""Regles metier des activites."""
from django.utils import timezone

from .models import Activity


def generer_code(quand=None):
    """Code d'activite de la forme ACT-2026-000123."""
    annee = (quand or timezone.now()).year
    prefixe = f"ACT-{annee}-"
    dernier = (
        Activity.objects.filter(code__startswith=prefixe)
        .order_by("-code")
        .values_list("code", flat=True)
        .first()
    )
    numero = int(dernier.rsplit("-", 1)[1]) + 1 if dernier else 1
    return f"{prefixe}{numero:06d}"


def activites_accessibles(user):
    """Activites relevant des projets accessibles a l'utilisateur."""
    from authorization.scopes import a_portee_globale, projets_accessibles

    if a_portee_globale(user):
        return Activity.objects.all()
    return Activity.objects.filter(project__in=projets_accessibles(user))