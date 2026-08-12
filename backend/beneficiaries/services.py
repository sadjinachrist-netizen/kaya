"""Regles metier des beneficiaires."""
import unicodedata
from decimal import Decimal

from django.contrib.postgres.search import TrigramSimilarity
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Consent, DuplicateCandidate, Household, Person

SEUIL_DOUBLON = Decimal("0.85")


def normaliser(texte):
    """Majuscules, sans accents, espaces reduits — pour comparer des noms."""
    sans_accent = unicodedata.normalize("NFKD", texte or "")
    sans_accent = "".join(c for c in sans_accent if not unicodedata.combining(c))
    return " ".join(sans_accent.upper().split())


def generer_code(quand=None):
    """Identifiant beneficiaire de la forme BEN-2026-000123."""
    annee = (quand or timezone.now()).year
    prefixe = f"BEN-{annee}-"
    dernier = (
        Household.objects.filter(code__startswith=prefixe)
        .order_by("-code")
        .values_list("code", flat=True)
        .first()
    )
    numero = int(dernier.rsplit("-", 1)[1]) + 1 if dernier else 1
    return f"{prefixe}{numero:06d}"


def chercher_doublons(nom_chef, zone, exclure=None, seuil=SEUIL_DOUBLON):
    """Menages de la meme localite dont le chef porte un nom proche.

    La comparaison est faite par PostgreSQL via pg_trgm, sur le nom
    normalise. La localite borne la recherche : deux homonymes dans
    deux prefectures differentes ne sont pas des doublons.
    """
    requete = (
        Household.objects.filter(zone=zone)
        .exclude(validation_status=Household.ValidationStatus.DOUBLON)
        .annotate(similarite=TrigramSimilarity("head_name", normaliser(nom_chef)))
        .filter(similarite__gte=float(seuil))
        .order_by("-similarite")
    )
    if exclure is not None:
        requete = requete.exclude(pk=exclure.pk)
    return requete


@transaction.atomic
def enregistrer_menage(*, agent, donnees, membres, consentement, projet=None):
    """Cree un menage, ses membres et son consentement, en une transaction.

    Applique la regle 8.4 du cahier d'analyse : aucun menage ne peut
    exister sans consentement accorde.
    """
    if not consentement.get("granted"):
        raise ValidationError(
            _("Le consentement du beneficiaire est obligatoire pour l'enregistrement.")
        )
    if not membres:
        raise ValidationError(_("Un menage comporte au moins un membre."))

    menage = Household(
        code=donnees.get("code") or generer_code(),
        head_name=normaliser(donnees["head_name"]),
        size=donnees.get("size") or len(membres),
        zone=donnees["zone"],
        latitude=donnees.get("latitude"),
        longitude=donnees.get("longitude"),
        gps_accuracy=donnees.get("gps_accuracy"),
        residence_status=donnees.get("residence_status", Household.ResidenceStatus.RESIDENT),
        registered_by=agent,
        client_uuid=donnees.get("client_uuid"),
    )
    menage.full_clean(exclude=["code"])
    menage.save()

    if donnees.get("vulnerabilities"):
        menage.vulnerabilities.set(donnees["vulnerabilities"])

    for membre in membres:
        Person.objects.create(household=menage, **membre)

    Consent.objects.create(
        household=menage,
        granted=True,
        collection_mode=consentement["collection_mode"],
        collected_at=consentement.get("collected_at") or timezone.now(),
    )

    if projet is not None:
        from .models import HouseholdProject

        HouseholdProject.objects.get_or_create(household=menage, project=projet)

    # Detection des doublons potentiels
    candidats = []
    for proche in chercher_doublons(menage.head_name, menage.zone, exclure=menage):
        candidats.append(
            DuplicateCandidate(
                household_a=proche,
                household_b=menage,
                score=round(Decimal(str(proche.similarite)), 3),
            )
        )
    if candidats:
        DuplicateCandidate.objects.bulk_create(candidats, ignore_conflicts=True)

    return menage, candidats


@transaction.atomic
def arbitrer_doublon(candidat, *, confirme, arbitre_par):
    """Tranche un doublon candidat.

    En cas de confirmation, le menage le plus recent est marque comme
    doublon : il reste en base, avec son historique, mais sort des
    comptages. Rien n'est supprime.
    """
    candidat.status = (
        DuplicateCandidate.Status.CONFIRME if confirme else DuplicateCandidate.Status.ECARTE
    )
    candidat.reviewed_by = arbitre_par
    candidat.reviewed_at = timezone.now()
    candidat.save()

    if confirme:
        recent = max(
            (candidat.household_a, candidat.household_b),
            key=lambda m: m.registered_at,
        )
        recent.validation_status = Household.ValidationStatus.DOUBLON
        recent.save(update_fields=["validation_status"])
    return candidat


def menages_accessibles(user):
    """Menages visibles par l'utilisateur, selon sa portee."""
    from django.db.models import Q

    from authorization.scopes import a_portee_globale, projets_accessibles

    if a_portee_globale(user):
        return Household.objects.all()
    return Household.objects.filter(
        Q(project_links__project__in=projets_accessibles(user))
        | Q(registered_by=user)
    ).distinct()