"""Verifie que l'API applique permissions et portee."""
import pytest

from audit.models import AuditLog


@pytest.mark.django_db
def test_acces_refuse_sans_jeton(api, projets):
    assert api.get("/api/projets/").status_code == 401


@pytest.mark.django_db
def test_agent_ne_recoit_que_ses_projets(api, connecte, agent_affecte, projets):
    connecte(agent_affecte)
    reponse = api.get("/api/projets/")
    assert reponse.status_code == 200
    assert [p["code"] for p in reponse.data["results"]] == ["PRJ-KARA"]


@pytest.mark.django_db
def test_chef_recoit_ses_deux_projets(api, connecte, chef, projets):
    connecte(chef)
    reponse = api.get("/api/projets/")
    assert reponse.status_code == 200
    assert reponse.data["count"] == 2


@pytest.mark.django_db
def test_agent_ne_peut_pas_creer_de_projet(api, connecte, agent_affecte, projets):
    connecte(agent_affecte)
    reponse = api.post(
        "/api/projets/",
        {
            "code": "PRJ-INTERDIT",
            "title": "Tentative",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
        },
        format="json",
    )
    assert reponse.status_code == 403


@pytest.mark.django_db
def test_un_refus_est_journalise(api, connecte, agent_affecte, projets):
    connecte(agent_affecte)
    api.post("/api/projets/", {"code": "X", "title": "X",
                               "start_date": "2026-01-01",
                               "end_date": "2026-12-31"}, format="json")
    refus = AuditLog.objects.filter(
        action=AuditLog.Action.ACCES_REFUSE, actor=agent_affecte
    )
    assert refus.exists()
    assert "projet.creer" in refus.first().detail


@pytest.mark.django_db
def test_connexion_renvoie_les_permissions(api, agent, referentiels):
    reponse = api.post(
        "/api/auth/login",
        {"email": agent.email, "password": "MotDePasse2026"},
        format="json",
    )
    assert reponse.status_code == 200
    permissions = reponse.data["user"]["permissions"]
    assert "activite.creer" in permissions
    assert "projet.creer" not in permissions