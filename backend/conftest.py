"""Fixtures partagees par tous les tests."""
import pytest
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from authorization.models import Role
from projects.models import InterventionSite, Project, TeamMember
from referentials.models import Sector, Zone


@pytest.fixture(scope="session")
def referentiels(django_db_setup, django_db_blocker):
    """Charge une seule fois les habilitations et la geographie."""
    with django_db_blocker.unblock():
        call_command("init_habilitations")
        call_command("init_referentiels")


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def agent(db, referentiels):
    utilisateur = User.objects.create_user(
        email="agent@test.tg", username="agent", password="MotDePasse2026",
        first_name="Kossi", last_name="Amegan",
    )
    Role.objects.get(code="agent_terrain").users.add(utilisateur)
    return utilisateur


@pytest.fixture
def chef(db, referentiels):
    utilisateur = User.objects.create_user(
        email="chef@test.tg", username="chef", password="MotDePasse2026",
        first_name="Afi", last_name="Doe",
    )
    Role.objects.get(code="chef_projet").users.add(utilisateur)
    return utilisateur


@pytest.fixture
def projets(db, referentiels, chef):
    """Deux projets dans deux regions differentes."""
    nutrition = Sector.objects.get(code="nutrition")
    sante = Sector.objects.get(code="sante")

    kara = Project.objects.create(
        code="PRJ-KARA", title="Nutrition communautaire Kara",
        start_date="2026-01-01", end_date="2027-06-30",
        manager=chef, target_beneficiaries=1800,
    )
    kara.sectors.add(nutrition)
    InterventionSite.objects.create(
        project=kara, zone=Zone.objects.get(code="kozah"), target_population=12000
    )

    savanes = Project.objects.create(
        code="PRJ-SAVANES", title="Sante maternelle Savanes",
        start_date="2026-03-01", end_date="2027-12-31",
        manager=chef, target_beneficiaries=2400,
    )
    savanes.sectors.add(sante)
    InterventionSite.objects.create(
        project=savanes, zone=Zone.objects.get(code="tone"), target_population=9000
    )
    return {"kara": kara, "savanes": savanes}


@pytest.fixture
def agent_affecte(agent, projets):
    """Agent affecte au seul projet de la Kara."""
    TeamMember.objects.create(
        project=projets["kara"], user=agent,
        project_role=TeamMember.ProjectRole.AGENT,
    )
    return agent


@pytest.fixture
def connecte(api):
    """Renvoie une fonction qui authentifie le client pour un utilisateur."""
    def _connecter(utilisateur, mot_de_passe="MotDePasse2026"):
        reponse = api.post(
            "/api/auth/login",
            {"email": utilisateur.email, "password": mot_de_passe},
            format="json",
        )
        assert reponse.status_code == 200, reponse.data
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {reponse.data['access']}")
        return reponse.data
    return _connecter