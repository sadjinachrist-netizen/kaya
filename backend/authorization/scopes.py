"""Resolution de la portee d'un utilisateur.

Point d'entree unique du filtrage par portee. Toute requete de lecture
sur des donnees rattachees a un projet doit passer par ici.
"""
from django.db.models import Q
from django.utils import timezone

from referentials.models import Zone

from .models import UserScope


def portees_actives(user):
    """Portees de l'utilisateur valides a la date du jour."""
    aujourdhui = timezone.localdate()
    return UserScope.objects.filter(user=user).filter(
        Q(start_date__isnull=True) | Q(start_date__lte=aujourdhui),
        Q(end_date__isnull=True) | Q(end_date__gte=aujourdhui),
    )


def a_portee_globale(user):
    if user.is_superuser:
        return True
    return portees_actives(user).filter(scope_type=UserScope.Type.GLOBAL).exists()


def zones_avec_descendants(zone_ids):
    """Etend un ensemble de zones a toute leur descendance.

    Une portee sur la region Kara donne acces a ses prefectures,
    cantons et villages.
    """
    resultat = set(zone_ids)
    niveau = list(zone_ids)
    while niveau:
        enfants = list(
            Zone.objects.filter(parent_id__in=niveau)
            .exclude(id__in=resultat)
            .values_list("id", flat=True)
        )
        if not enfants:
            break
        resultat.update(enfants)
        niveau = enfants
    return resultat


def projets_accessibles(user):
    """Projets que l'utilisateur a le droit de voir.

    Trois sources cumulatives :
      1. une portee explicite (projet ou zone) accordee par l'administrateur ;
      2. une affectation active dans l'equipe du projet ;
      3. la direction du projet.

    Les deux dernieres evitent d'avoir a declarer une portee pour chaque
    agent sur chaque projet, ce qui serait ingerable en exploitation.
    """
    from projects.models import Project

    if a_portee_globale(user):
        return Project.objects.all()

    portees = portees_actives(user)

    projets_directs = portees.filter(
        scope_type=UserScope.Type.PROJECT
    ).values_list("project_id", flat=True)

    zones = list(
        portees.filter(scope_type=UserScope.Type.ZONE).values_list("zone_id", flat=True)
    )
    zones_etendues = zones_avec_descendants(zones) if zones else set()

    aujourdhui = timezone.localdate()
    return (
        Project.objects.filter(
            Q(pk__in=list(projets_directs))
            | Q(sites__zone_id__in=zones_etendues)
            | Q(manager=user)
            | (
                Q(members__user=user)
                & Q(members__start_date__lte=aujourdhui)
                & (Q(members__end_date__isnull=True) | Q(members__end_date__gte=aujourdhui))
            )
        )
        .distinct()
    )


def filtrer_par_portee(queryset, user, chemin_projet="project"):
    """Restreint un queryset aux objets rattaches aux projets accessibles.

    `chemin_projet` est le chemin ORM menant au projet depuis le modele
    filtre : "project" pour Activity, "household__projects" pour Person, etc.
    """
    if a_portee_globale(user):
        return queryset
    return queryset.filter(
        **{f"{chemin_projet}__in": projets_accessibles(user)}
    ).distinct()