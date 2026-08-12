"""Portee des financements."""
from .models import Grant


def financements_accessibles(user):
    """Financements rattaches aux projets accessibles a l'utilisateur."""
    from authorization.scopes import a_portee_globale, projets_accessibles

    if a_portee_globale(user):
        return Grant.objects.all()
    return Grant.objects.filter(
        project_links__project__in=projets_accessibles(user)
    ).distinct()