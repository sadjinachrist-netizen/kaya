"""Beneficiaires - paquetage P5 du cahier d'analyse.

L'unite d'enregistrement est le MENAGE, conformement a la pratique du
secteur humanitaire : l'assistance se planifie par menage, les effectifs
se comptent par individu, desagreges par sexe et tranche d'age.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from referentials.models import Zone


class Vulnerability(models.Model):
    """Critere de vulnerabilite applicable a un menage."""

    code = models.SlugField(_("code"), max_length=50, unique=True)
    label = models.CharField(_("intitule"), max_length=150)
    weight = models.PositiveSmallIntegerField(
        _("poids"), default=1, help_text=_("Contribution au score de vulnerabilite.")
    )
    is_active = models.BooleanField(_("actif"), default=True)

    class Meta:
        verbose_name = _("critere de vulnerabilite")
        verbose_name_plural = _("criteres de vulnerabilite")
        ordering = ["-weight", "label"]

    def __str__(self):
        return self.label


class Household(models.Model):
    """Menage beneficiaire."""

    class ResidenceStatus(models.TextChoices):
        RESIDENT = "resident", _("Resident")
        DEPLACE = "deplace", _("Deplace interne")
        REFUGIE = "refugie", _("Refugie")
        RETOURNE = "retourne", _("Retourne")

    class ValidationStatus(models.TextChoices):
        A_VALIDER = "a_valider", _("A valider")
        VALIDE = "valide", _("Valide")
        DOUBLON = "doublon", _("Doublon confirme")

    code = models.CharField(_("identifiant beneficiaire"), max_length=30, unique=True)

    # Champ nominatif protege : restitue seulement aux roles habilites
    head_name = models.CharField(_("nom du chef de menage"), max_length=200)
    size = models.PositiveSmallIntegerField(_("taille du menage"), default=1)

    zone = models.ForeignKey(
        Zone, on_delete=models.PROTECT, related_name="households", verbose_name=_("localite")
    )
    latitude = models.DecimalField(
        _("latitude"), max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        _("longitude"), max_digits=9, decimal_places=6, null=True, blank=True
    )
    gps_accuracy = models.PositiveSmallIntegerField(
        _("precision GPS (m)"), null=True, blank=True
    )

    residence_status = models.CharField(
        _("statut de residence"), max_length=15,
        choices=ResidenceStatus.choices, default=ResidenceStatus.RESIDENT,
    )
    vulnerabilities = models.ManyToManyField(
        Vulnerability, blank=True, related_name="households",
        verbose_name=_("vulnerabilites"),
    )

    registered_at = models.DateTimeField(_("enregistre le"), default=timezone.now)
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="households_registered", verbose_name=_("enregistre par"),
    )
    validation_status = models.CharField(
        _("statut de validation"), max_length=15,
        choices=ValidationStatus.choices, default=ValidationStatus.A_VALIDER,
    )

    # Identifiant genere hors ligne : garantit l'idempotence de la synchronisation
    client_uuid = models.UUIDField(_("identifiant client"), unique=True, null=True, blank=True)

    class Meta:
        verbose_name = _("menage")
        verbose_name_plural = _("menages")
        ordering = ["-registered_at"]
        indexes = [
            models.Index(fields=["zone", "validation_status"]),
            models.Index(fields=["registered_by", "-registered_at"]),
        ]

    def __str__(self):
        return f"{self.code} — {self.head_name}"

    @property
    def vulnerability_score(self):
        return sum(v.weight for v in self.vulnerabilities.all())

    @property
    def sadd(self):
        """Effectifs desagreges par sexe et tranche d'age (format bailleur)."""
        tranches = {"0_5": [0, 0], "6_17": [0, 0], "18_59": [0, 0], "60_plus": [0, 0]}
        for personne in self.members.all():
            age = personne.age
            if age is None:
                continue
            if age <= 5:
                cle = "0_5"
            elif age <= 17:
                cle = "6_17"
            elif age <= 59:
                cle = "18_59"
            else:
                cle = "60_plus"
            tranches[cle][0 if personne.sex == Person.Sex.MASCULIN else 1] += 1
        return {
            cle: {"hommes": valeurs[0], "femmes": valeurs[1]}
            for cle, valeurs in tranches.items()
        }


class Person(models.Model):
    """Individu membre d'un menage. Composition avec Household."""

    class Sex(models.TextChoices):
        MASCULIN = "M", _("Masculin")
        FEMININ = "F", _("Feminin")

    household = models.ForeignKey(
        Household, on_delete=models.CASCADE, related_name="members", verbose_name=_("menage")
    )
    # Champs nominatifs proteges
    first_name = models.CharField(_("prenom"), max_length=100)
    last_name = models.CharField(_("nom"), max_length=100, blank=True)

    sex = models.CharField(_("sexe"), max_length=1, choices=Sex.choices)
    birth_date = models.DateField(_("date de naissance"), null=True, blank=True)
    estimated_age = models.PositiveSmallIntegerField(
        _("age estime"), null=True, blank=True,
        help_text=_("A renseigner lorsque la date de naissance est inconnue."),
    )
    relation_to_head = models.CharField(_("lien avec le chef de menage"), max_length=60, blank=True)
    is_head = models.BooleanField(_("chef de menage"), default=False)
    is_enrolled = models.BooleanField(_("scolarise"), default=False)
    has_disability = models.BooleanField(_("situation de handicap"), default=False)

    class Meta:
        verbose_name = _("individu")
        verbose_name_plural = _("individus")
        ordering = ["-is_head", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()

    def clean(self):
        if self.birth_date is None and self.estimated_age is None:
            raise ValidationError(
                _("Renseignez une date de naissance ou un age estime.")
            )
        if self.birth_date and self.birth_date > timezone.localdate():
            raise ValidationError({"birth_date": _("Date de naissance dans le futur.")})

    @property
    def age(self):
        if self.birth_date:
            aujourdhui = timezone.localdate()
            return (
                aujourdhui.year - self.birth_date.year
                - ((aujourdhui.month, aujourdhui.day) < (self.birth_date.month, self.birth_date.day))
            )
        return self.estimated_age


class Consent(models.Model):
    """Consentement du beneficiaire au traitement de ses donnees.

    Sans consentement accorde, aucun menage ne peut etre enregistre
    (regle de gestion 8.4).
    """

    class Mode(models.TextChoices):
        ECRIT = "ecrit", _("Ecrit")
        ORAL = "oral", _("Oral")
        EMPREINTE = "empreinte", _("Empreinte")

    household = models.OneToOneField(
        Household, on_delete=models.CASCADE, related_name="consent", verbose_name=_("menage")
    )
    granted = models.BooleanField(_("consentement accorde"), default=False)
    collection_mode = models.CharField(_("mode de recueil"), max_length=15, choices=Mode.choices)
    collected_at = models.DateTimeField(_("recueilli le"), default=timezone.now)
    withdrawn_at = models.DateTimeField(_("retire le"), null=True, blank=True)

    class Meta:
        verbose_name = _("consentement")
        verbose_name_plural = _("consentements")

    def __str__(self):
        etat = "accorde" if self.is_valid else "retire ou refuse"
        return f"Consentement {self.household.code} — {etat}"

    @property
    def is_valid(self):
        return self.granted and self.withdrawn_at is None


class HouseholdProject(models.Model):
    """Rattachement d'un menage a un projet."""

    class ReachType(models.TextChoices):
        ATTEINT = "atteint", _("Atteint")
        ASSISTE = "assiste", _("Assiste")

    household = models.ForeignKey(
        Household, on_delete=models.CASCADE, related_name="project_links",
        verbose_name=_("menage"),
    )
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="household_links",
        verbose_name=_("projet"),
    )
    linked_at = models.DateField(_("rattache le"), default=timezone.localdate)
    reach_type = models.CharField(
        _("type d'atteinte"), max_length=10,
        choices=ReachType.choices, default=ReachType.ATTEINT,
    )

    class Meta:
        verbose_name = _("rattachement a un projet")
        verbose_name_plural = _("rattachements aux projets")
        constraints = [
            models.UniqueConstraint(
                fields=["household", "project"], name="unique_menage_projet"
            )
        ]

    def __str__(self):
        return f"{self.household.code} → {self.project.code}"


class DuplicateCandidate(models.Model):
    """Doublon potentiel detecte entre deux menages."""

    class Status(models.TextChoices):
        A_ARBITRER = "a_arbitrer", _("A arbitrer")
        CONFIRME = "confirme", _("Doublon confirme")
        ECARTE = "ecarte", _("Menages distincts")

    household_a = models.ForeignKey(
        Household, on_delete=models.CASCADE, related_name="duplicates_as_a",
        verbose_name=_("menage A"),
    )
    household_b = models.ForeignKey(
        Household, on_delete=models.CASCADE, related_name="duplicates_as_b",
        verbose_name=_("menage B"),
    )
    score = models.DecimalField(_("score de proximite"), max_digits=4, decimal_places=3)
    status = models.CharField(
        _("statut"), max_length=15, choices=Status.choices, default=Status.A_ARBITRER
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="duplicates_reviewed", verbose_name=_("arbitre par"),
    )
    reviewed_at = models.DateTimeField(_("arbitre le"), null=True, blank=True)

    class Meta:
        verbose_name = _("doublon candidat")
        verbose_name_plural = _("doublons candidats")
        ordering = ["-score"]
        constraints = [
            models.UniqueConstraint(
                fields=["household_a", "household_b"], name="unique_paire_doublon"
            )
        ]

    def __str__(self):
        return f"{self.household_a.code} ≈ {self.household_b.code} ({self.score})"