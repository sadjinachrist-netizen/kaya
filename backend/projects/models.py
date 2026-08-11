"""Projets et equipes - paquetage P3 du cahier d'analyse."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from referentials.models import Sector, Zone


class Project(models.Model):
    """Projet mis en oeuvre par l'ONG. Objet pivot du systeme."""

    class Status(models.TextChoices):
        BROUILLON = "brouillon", _("Brouillon")
        EN_INSTRUCTION = "en_instruction", _("En instruction")
        APPROUVE = "approuve", _("Approuve")
        EN_COURS = "en_cours", _("En cours")
        SUSPENDU = "suspendu", _("Suspendu")
        CLOTURE = "cloture", _("Cloture")
        ARCHIVE = "archive", _("Archive")

    # Cycle de vie : seules ces transitions sont autorisees
    TRANSITIONS = {
        Status.BROUILLON: [Status.EN_INSTRUCTION],
        Status.EN_INSTRUCTION: [Status.APPROUVE, Status.BROUILLON],
        Status.APPROUVE: [Status.EN_COURS],
        Status.EN_COURS: [Status.SUSPENDU, Status.CLOTURE],
        Status.SUSPENDU: [Status.EN_COURS],
        Status.CLOTURE: [Status.ARCHIVE],
        Status.ARCHIVE: [],
    }

    # Transitions exigeant un motif ecrit
    MOTIF_OBLIGATOIRE = {Status.SUSPENDU, Status.BROUILLON}

    code = models.SlugField(_("code projet"), max_length=30, unique=True)
    title = models.CharField(_("intitule"), max_length=200)
    description = models.TextField(_("description"), blank=True)

    sectors = models.ManyToManyField(
        Sector, related_name="projects", verbose_name=_("secteurs d'intervention")
    )

    start_date = models.DateField(_("date de debut"))
    end_date = models.DateField(_("date de fin prevue"))

    status = models.CharField(
        _("statut"), max_length=20, choices=Status.choices, default=Status.BROUILLON
    )
    target_beneficiaries = models.PositiveIntegerField(
        _("beneficiaires vises"), default=0
    )
    progress_rate = models.PositiveSmallIntegerField(_("taux d'avancement"), default=0)

    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="managed_projects",
        verbose_name=_("chef de projet"),
    )

    created_at = models.DateTimeField(_("cree le"), auto_now_add=True)
    updated_at = models.DateTimeField(_("modifie le"), auto_now=True)

    class Meta:
        verbose_name = _("projet")
        verbose_name_plural = _("projets")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["manager", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gt=models.F("start_date")),
                name="projet_fin_apres_debut",
            )
        ]

    def __str__(self):
        return f"{self.code} — {self.title}"

    def clean(self):
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValidationError(
                {"end_date": _("La date de fin doit etre posterieure a la date de debut.")}
            )

    # ------------------------------------------------------- Cycle de vie
    @property
    def transitions_possibles(self):
        return self.TRANSITIONS[self.status]

    def changer_statut(self, nouveau_statut, *, auteur=None, motif=""):
        """Fait evoluer le projet dans son cycle de vie.

        Toute transition est controlee, tracee, et refusee si elle n'est pas
        prevue par le cycle de vie.
        """
        from audit.models import AuditLog
        from audit.services import journaliser

        if nouveau_statut not in self.TRANSITIONS[self.status]:
            raise ValidationError(
                _("Transition impossible : %(de)s vers %(vers)s.")
                % {"de": self.get_status_display(), "vers": nouveau_statut}
            )
        if nouveau_statut in self.MOTIF_OBLIGATOIRE and not motif:
            raise ValidationError(_("Un motif est obligatoire pour cette transition."))

        ancien = self.status
        self.status = nouveau_statut
        self.save(update_fields=["status", "updated_at"])

        journaliser(
            AuditLog.Action.MODIFICATION,
            actor=auteur,
            obj=self,
            old_value={"status": ancien},
            new_value={"status": nouveau_statut},
            detail=motif or f"Passage de {ancien} a {nouveau_statut}",
        )
        return self

    # ------------------------------------------------------- Avancement
    @property
    def avancement_temporel(self):
        """Part du calendrier deja ecoulee, en pourcentage."""
        aujourdhui = timezone.localdate()
        if aujourdhui <= self.start_date:
            return 0
        if aujourdhui >= self.end_date:
            return 100
        total = (self.end_date - self.start_date).days
        ecoule = (aujourdhui - self.start_date).days
        return round(ecoule / total * 100) if total else 0

    def calculer_avancement(self):
        """Avancement decompose en trois composantes explicables.

        Contrairement a la v1, aucune ponderation arbitraire : chaque
        composante est affichee separement dans le tableau de bord.
        Les deux dernieres seront branchees avec les indicateurs (P6)
        et le budget (P4).
        """
        return {
            "temporel": self.avancement_temporel,
            "indicateurs": None,   # a brancher avec IndicatorReading
            "budgetaire": None,    # a brancher avec Expense
        }


class InterventionSite(models.Model):
    """Localite sur laquelle un projet intervient. Composition avec Project."""

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="sites", verbose_name=_("projet")
    )
    zone = models.ForeignKey(
        Zone, on_delete=models.PROTECT, related_name="sites", verbose_name=_("zone")
    )
    latitude = models.DecimalField(
        _("latitude"), max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        _("longitude"), max_digits=9, decimal_places=6, null=True, blank=True
    )
    target_population = models.PositiveIntegerField(_("population cible"), default=0)

    class Meta:
        verbose_name = _("site d'intervention")
        verbose_name_plural = _("sites d'intervention")
        ordering = ["zone__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "zone"], name="unique_site_par_projet"
            )
        ]

    def __str__(self):
        return f"{self.zone.name} ({self.project.code})"


class TeamMember(models.Model):
    """Affectation datee d'un utilisateur a un projet, avec son role."""

    class ProjectRole(models.TextChoices):
        CHEF = "chef", _("Chef de projet")
        SUPERVISEUR = "superviseur", _("Superviseur terrain")
        AGENT = "agent", _("Agent terrain")
        SUIVI = "suivi_evaluation", _("Charge de suivi-evaluation")

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="members", verbose_name=_("projet")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="project_memberships",
        verbose_name=_("utilisateur"),
    )
    project_role = models.CharField(
        _("role sur le projet"), max_length=20, choices=ProjectRole.choices
    )
    start_date = models.DateField(_("debut d'affectation"), default=timezone.localdate)
    end_date = models.DateField(_("fin d'affectation"), null=True, blank=True)

    class Meta:
        verbose_name = _("membre d'equipe")
        verbose_name_plural = _("membres d'equipe")
        ordering = ["project", "user"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "user", "project_role", "start_date"],
                name="unique_affectation",
            )
        ]

    def __str__(self):
        return f"{self.user.username} — {self.get_project_role_display()} ({self.project.code})"

    def clean(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": _("La fin d'affectation ne peut preceder son debut.")}
            )

    @property
    def is_active(self):
        aujourdhui = timezone.localdate()
        return self.start_date <= aujourdhui and (
            self.end_date is None or self.end_date >= aujourdhui
        )


class Amendment(models.Model):
    """Avenant modifiant la duree, le montant ou le perimetre d'un projet."""

    class Type(models.TextChoices):
        DUREE = "duree", _("Duree")
        MONTANT = "montant", _("Montant")
        PERIMETRE = "perimetre", _("Perimetre")

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="amendments", verbose_name=_("projet")
    )
    type = models.CharField(_("type"), max_length=15, choices=Type.choices)
    old_value = models.CharField(_("valeur avant"), max_length=255)
    new_value = models.CharField(_("valeur apres"), max_length=255)
    effective_date = models.DateField(_("date d'effet"))
    reason = models.TextField(_("motif"))

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="amendments",
        verbose_name=_("saisi par"),
    )
    created_at = models.DateTimeField(_("cree le"), auto_now_add=True)

    class Meta:
        verbose_name = _("avenant")
        verbose_name_plural = _("avenants")
        ordering = ["-effective_date"]

    def __str__(self):
        return f"Avenant {self.get_type_display()} — {self.project.code}"