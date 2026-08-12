"""Verifie le cloisonnement des donnees par portee."""
from datetime import timedelta

import pytest
from django.db.utils import IntegrityError
from django.utils import timezone

from authorization.models import UserScope
from authorization.scopes import projets_accessibles


def codes(queryset):
    return sorted(queryset.values_list("code", flat=True))


@pytest.mark.django_db
def test_agent_ne_voit_que_ses_projets(agent_affecte, projets):
    assert codes(projets_accessibles(agent_affecte)) == ["PRJ-KARA"]


@pytest.mark.django_db
def test_chef_voit_les_projets_qu_il_dirige(chef, projets):
    assert codes(projets_accessibles(chef)) == ["PRJ-KARA", "PRJ-SAVANES"]


@pytest.mark.django_db
def test_portee_sur_une_region_ouvre_ses_prefectures(agent_affecte, projets):
    from referentials.models import Zone

    UserScope.objects.create(
        user=agent_affecte,
        scope_type=UserScope.Type.ZONE,
        zone=Zone.objects.get(code="savanes"),
    )
    # Le projet Savanes intervient a Tone, prefecture de la region Savanes
    assert codes(projets_accessibles(agent_affecte)) == ["PRJ-KARA", "PRJ-SAVANES"]


@pytest.mark.django_db
def test_portee_expiree_ne_donne_plus_acces(agent_affecte, projets):
    from referentials.models import Zone

    UserScope.objects.create(
        user=agent_affecte,
        scope_type=UserScope.Type.ZONE,
        zone=Zone.objects.get(code="savanes"),
        end_date=timezone.localdate() - timedelta(days=1),
    )
    assert codes(projets_accessibles(agent_affecte)) == ["PRJ-KARA"]


@pytest.mark.django_db
def test_portee_incoherente_refusee_par_la_base(agent, projets):
    with pytest.raises(IntegrityError):
        UserScope.objects.create(
            user=agent,
            scope_type=UserScope.Type.ZONE,
            project=projets["kara"],  # incoherent : type zone mais projet designe
        )