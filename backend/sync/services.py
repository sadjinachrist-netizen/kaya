"""Preparation des lots hors ligne et reception des saisies.

Deux operations, decrites par le diagramme de sequence 7.3 du cahier
d'analyse :

  - construire_lot()   : tout ce dont l'agent a besoin avant de partir ;
  - traiter_element()  : reception idempotente d'une saisie remontee.

L'idempotence repose sur `client_uuid`, un identifiant genere par
l'appareil avant meme que la donnee n'atteigne le serveur. Un renvoi
apres coupure reseau ne cree donc jamais de doublon.
"""
from django.db import transaction
from django.utils import timezone

from activities.models import Activity, ActivityParticipation
from activities.services import generer_code as generer_code_activite
from authorization.scopes import projets_accessibles
from beneficiaries.models import Household, Vulnerability
from beneficiaries.services import enregistrer_menage
from referentials.models import Sector, Zone

# Statuts renvoyes pour chaque element remonte
CREE = "cree"
DEJA_TRAITE = "deja_traite"
ERREUR = "erreur"


def construire_lot(user):
    """Donnees a precharger sur l'appareil avant depart en mission."""
    projets = projets_accessibles(user).filter(status="en_cours")

    zones_utiles = Zone.objects.filter(
        sites__project__in=projets
    ).select_related("parent").distinct()
    # On embarque aussi les zones filles, pour permettre une saisie fine
    descendants = Zone.objects.filter(parent__in=zones_utiles)

    menages = Household.objects.filter(
        project_links__project__in=projets
    ).exclude(
        validation_status=Household.ValidationStatus.DOUBLON
    ).select_related("zone").distinct()

    return {
        "genere_le": timezone.now(),
        "agent": {"id": user.id, "username": user.username, "nom": user.full_name},
        "projets": [
            {
                "id": p.id, "code": p.code, "titre": p.title,
                "debut": p.start_date, "fin": p.end_date,
                "zones": list(p.sites.values_list("zone_id", flat=True)),
            }
            for p in projets.prefetch_related("sites")
        ],
        "zones": [
            {"id": z.id, "code": z.code, "nom": z.name,
             "niveau": z.level, "parent": z.parent_id}
            for z in list(zones_utiles) + list(descendants)
        ],
        "secteurs": list(Sector.objects.filter(is_active=True).values("id", "code", "label")),
        "vulnerabilites": list(
            Vulnerability.objects.filter(is_active=True).values("id", "code", "label", "weight")
        ),
        "types_activite": [
            {"code": code, "libelle": libelle} for code, libelle in Activity.Type.choices
        ],
        "menages": [
            {
                "id": m.id, "code": m.code, "chef": m.head_name, "taille": m.size,
                "zone": m.zone_id, "statut": m.validation_status,
                "client_uuid": str(m.client_uuid) if m.client_uuid else None,
            }
            for m in menages
        ],
        "compteurs": {
            "projets": projets.count(),
            "menages": menages.count(),
            "zones": len(zones_utiles) + descendants.count(),
        },
    }


def _resultat(client_uuid, statut, **extra):
    return {"client_uuid": client_uuid, "statut": statut, **extra}


@transaction.atomic
def _creer_menage(user, client_uuid, donnees):
    zone = Zone.objects.get(pk=donnees["zone"])
    projet_id = donnees.get("projet")
    projet = None
    if projet_id:
        projet = projets_accessibles(user).filter(pk=projet_id).first()
        if projet is None:
            raise ValueError("Projet inaccessible ou inconnu.")

    vulnerabilites = Vulnerability.objects.filter(id__in=donnees.get("vulnerabilites", []))

    menage, doublons = enregistrer_menage(
        agent=user,
        donnees={
            "head_name": donnees["head_name"],
            "size": donnees.get("size"),
            "zone": zone,
            "latitude": donnees.get("latitude"),
            "longitude": donnees.get("longitude"),
            "gps_accuracy": donnees.get("gps_accuracy"),
            "residence_status": donnees.get("residence_status", "resident"),
            "vulnerabilities": vulnerabilites,
            "client_uuid": client_uuid,
        },
        membres=donnees["membres"],
        consentement=donnees["consentement"],
        projet=projet,
    )
    return _resultat(
        client_uuid, CREE, id=menage.id, code=menage.code,
        doublons_detectes=[
            {"menage": c.household_a.code, "score": str(c.score)} for c in doublons
        ],
    )


@transaction.atomic
def _creer_activite(user, client_uuid, donnees):
    projet = projets_accessibles(user).filter(pk=donnees["projet"]).first()
    if projet is None:
        raise ValueError("Projet inaccessible ou inconnu.")

    activite = Activity(
        code=generer_code_activite(),
        project=projet,
        type=donnees["type"],
        activity_date=donnees["activity_date"],
        zone=Zone.objects.get(pk=donnees["zone"]),
        description=donnees.get("description", ""),
        results=donnees.get("results", ""),
        latitude=donnees.get("latitude"),
        longitude=donnees.get("longitude"),
        gps_accuracy=donnees.get("gps_accuracy"),
        entry_duration_seconds=donnees.get("entry_duration_seconds"),
        agent=user,
        client_uuid=client_uuid,
        status=Activity.Status.SYNCHRONISEE,
    )
    activite.full_clean(exclude=["code"])
    activite.save()

    for participation in donnees.get("participations", []):
        ActivityParticipation.objects.create(
            activity=activite,
            household_id=participation.get("household"),
            males_count=participation.get("males_count", 0),
            females_count=participation.get("females_count", 0),
            age_breakdown=participation.get("age_breakdown", {}),
        )

    if donnees.get("soumettre"):
        activite.soumettre(auteur=user)

    return _resultat(
        client_uuid, CREE, id=activite.id, code=activite.code,
        alertes=activite.alertes_qualite,
    )


CREATEURS = {"menage": _creer_menage, "activite": _creer_activite}
MODELES = {"menage": Household, "activite": Activity}


def traiter_element(user, element):
    """Traite un element remonte depuis l'appareil.

    Renvoie toujours un resultat, jamais d'exception : un element en
    erreur ne doit pas empecher le traitement des suivants.
    """
    client_uuid = element.get("client_uuid")
    type_element = element.get("type")

    if not client_uuid:
        return _resultat(None, ERREUR, erreurs=["client_uuid manquant."])
    if type_element not in CREATEURS:
        return _resultat(client_uuid, ERREUR, erreurs=[f"Type inconnu : {type_element}."])

    # Idempotence : si l'identifiant client existe deja, on ne recree rien
    existant = MODELES[type_element].objects.filter(client_uuid=client_uuid).first()
    if existant is not None:
        return _resultat(
            client_uuid, DEJA_TRAITE, id=existant.id, code=existant.code,
            message="Element deja enregistre, aucun doublon cree.",
        )

    try:
        return CREATEURS[type_element](user, client_uuid, element.get("donnees", {}))
    except Exception as erreur:  # noqa: BLE001 — on renvoie l'erreur au client
        detail = getattr(erreur, "message_dict", None) or [str(erreur)]
        return _resultat(client_uuid, ERREUR, erreurs=detail)