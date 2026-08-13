"""Activites terrain - paquetage P5 du cahier d'analyse."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from referentials.models import Zone


class Activity(models.Model):
    """Intervention realisee sur le terrain dans le cadre d'un projet."""

    class Type(models.TextChoices):
        FORMATION = "formation", _("Formation")
        SENSIBILISATION = "sensibilisation", _("Sensibilisation")
        DISTRIBUTION = "distribution", _("Distribution")
        VISITE = "visite", _("Visite de suivi")
        REUNION = "reunion", _("Reunion communautaire")
        ENQUETE = "enquete", _("Enquete")

    class Status(models.TextChoices):
        BROUILLON = "brouillon", _("Brouillon")
        SYNCHRONISEE = "synchronisee", _("Synchronisee")
        SOUMISE = "soumise", _("Soumise")
        VALIDEE = "validee", _("Validee")
        REJETEE = "rejetee", _("Rejetee")

    TRANSITIONS = {
        Status.BROUILLON: [Status.SYNCHRONISEE, Status.SOUMISE],
        Status.SYNCHRONISEE: [Status.SOUMISE],
        Status.SOUMISE: [Status.VALIDEE, Status.REJETEE],
        Status.VALIDEE: [],
        Status.REJETEE: [Status.BROUILLON],
    }

    # Types pour lesquels une piece justificative est attendue
    JUSTIFICATIF_ATTENDU = {Type.DISTRIBUTION, Type.FORMATION}

    code = models.CharField(_("code"), max_length=30, unique=True)
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE,
        related_name="activities", verbose_name=_("projet"),
    )
    type = models.CharField(_("type"), max_length=20, choices=Type.choices)

    # Date de realisation, distincte de la date de saisie
    activity_date = models.DateField(_("date de realisation"))
    zone = models.ForeignKey(
        Zone, on_delete=models.PROTECT, related_name="activities", verbose_name=_("localite")
    )
    description = models.TextField(_("description"))
    results = models.TextField(_("resultats obtenus"), blank=True)

    latitude = models.DecimalField(
        _("latitude"), max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        _("longitude"), max_digits=9, decimal_places=6, null=True, blank=True
    )
    gps_accuracy = models.PositiveSmallIntegerField(
        _("precision GPS (m)"), null=True, blank=True
    )

    status = models.CharField(
        _("statut"), max_length=15, choices=Status.choices, default=Status.BROUILLON
    )
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="activities", verbose_name=_("agent"),
    )

    submitted_at = models.DateTimeField(_("soumise le"), null=True, blank=True)
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="activities_validated", verbose_name=_("statuee par"),
    )
    validated_at = models.DateTimeField(_("statuee le"), null=True, blank=True)
    rejection_reason = models.TextField(_("motif de rejet"), blank=True)

    # Duree de saisie, utilisee par les controles qualite
    entry_duration_seconds = models.PositiveIntegerField(
        _("duree de saisie (s)"), null=True, blank=True
    )
    client_uuid = models.UUIDField(
        _("identifiant client"), unique=True, null=True, blank=True
    )
    created_at = models.DateTimeField(_("creee le"), auto_now_add=True)

    class Meta:
        verbose_name = _("activite")
        verbose_name_plural = _("activites")
        ordering = ["-activity_date", "-created_at"]
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["agent", "-activity_date"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.code} — {self.get_type_display()} ({self.project.code})"

    def clean(self):
        if self.activity_date and self.activity_date > timezone.localdate():
            raise ValidationError(
                {"activity_date": _("Une activite ne peut pas etre datee du futur.")}
            )
        if self.project_id and self.activity_date:
            if self.activity_date < self.project.start_date:
                raise ValidationError(
                    {"activity_date": _("Date anterieure au debut du projet.")}
                )

    # ------------------------------------------------------- Cycle de vie
    @property
    def transitions_possibles(self):
        return self.TRANSITIONS[self.status]

    @property
    def est_modifiable(self):
        """Une activite validee devient definitivement non modifiable."""
        return self.status in (self.Status.BROUILLON, self.Status.REJETEE)

    def _changer_statut(self, nouveau, *, auteur=None, motif=""):
        from audit.models import AuditLog
        from audit.services import journaliser

        if nouveau not in self.TRANSITIONS[self.status]:
            raise ValidationError(
                _("Transition impossible : %(de)s vers %(vers)s.")
                % {"de": self.get_status_display(), "vers": nouveau}
            )
        ancien = self.status
        self.status = nouveau
        champs = ["status"]

        if nouveau == self.Status.SOUMISE:
            self.submitted_at = timezone.now()
            champs.append("submitted_at")
        elif nouveau in (self.Status.VALIDEE, self.Status.REJETEE):
            self.validated_by = auteur
            self.validated_at = timezone.now()
            self.rejection_reason = motif
            champs += ["validated_by", "validated_at", "rejection_reason"]
        elif nouveau == self.Status.BROUILLON:
            self.rejection_reason = ""
            champs.append("rejection_reason")

        self.save(update_fields=champs)
        journaliser(
            AuditLog.Action.MODIFICATION,
            actor=auteur or self.agent,
            obj=self,
            old_value={"status": ancien},
            new_value={"status": nouveau},
            detail=motif or f"Passage de {ancien} a {nouveau}",
        )

                # Notifications du workflow de validation
        from notifications.services import activite_soumise, activite_statuee

        if nouveau == self.Status.SOUMISE:
            activite_soumise(self)
        elif nouveau in (self.Status.VALIDEE, self.Status.REJETEE):
            activite_statuee(self, validee=(nouveau == self.Status.VALIDEE))

        return self

    def soumettre(self, *, auteur=None):
        return self._changer_statut(self.Status.SOUMISE, auteur=auteur or self.agent)

    def valider(self, *, auteur):
        return self._changer_statut(self.Status.VALIDEE, auteur=auteur)

    def rejeter(self, *, auteur, motif):
        if not motif:
            raise ValidationError(_("Un motif est obligatoire pour rejeter une activite."))
        return self._changer_statut(self.Status.REJETEE, auteur=auteur, motif=motif)

    def corriger(self):
        return self._changer_statut(self.Status.BROUILLON, auteur=self.agent)

    # ---------------------------------------------------- Controle qualite
    @property
    def alertes_qualite(self):
        """Signaux d'alerte a l'attention du superviseur.

        Ces alertes n'empechent jamais la saisie : elles informent
        celui qui valide (regle de gestion 8.5).
        """
        alertes = []

        zones_projet = set(self.project.sites.values_list("zone_id", flat=True))
        if zones_projet:
            parent = self.zone.parent_id
            if self.zone_id not in zones_projet and parent not in zones_projet:
                alertes.append("Localite hors des sites d'intervention du projet")

        if self.entry_duration_seconds is not None and self.entry_duration_seconds < 30:
            alertes.append("Saisie anormalement rapide")

        if self.gps_accuracy is not None and self.gps_accuracy > 100:
            alertes.append("Position GPS imprecise")
        elif self.latitude is None:
            alertes.append("Aucune position GPS capturee")

        if self.type in self.JUSTIFICATIF_ATTENDU and not self.attachments.exists():
            alertes.append("Aucune piece justificative pour ce type d'activite")

        ecart = (timezone.localdate() - self.activity_date).days
        if ecart > 30:
            alertes.append(f"Saisie tardive ({ecart} jours apres la realisation)")

        return alertes

    @property
    def participants_totaux(self):
        agregat = self.participations.aggregate(
            hommes=models.Sum("males_count"), femmes=models.Sum("females_count")
        )
        return {
            "hommes": agregat["hommes"] or 0,
            "femmes": agregat["femmes"] or 0,
            "total": (agregat["hommes"] or 0) + (agregat["femmes"] or 0),
        }


class Attachment(models.Model):
    """Piece justificative rattachee a une activite."""

    TYPES_AUTORISES = ["image/jpeg", "image/png", "image/webp", "application/pdf"]
    TAILLE_MAX = 5 * 1024 * 1024  # 5 Mo

    activity = models.ForeignKey(
        Activity, on_delete=models.CASCADE, related_name="attachments",
        verbose_name=_("activite"),
    )
    file = models.FileField(_("fichier"), upload_to="justificatifs/%Y/%m/")
    mime_type = models.CharField(_("type de fichier"), max_length=100, blank=True)
    size = models.PositiveIntegerField(_("taille (octets)"), default=0)
    caption = models.CharField(_("legende"), max_length=255, blank=True)
    uploaded_at = models.DateTimeField(_("depose le"), auto_now_add=True)

    class Meta:
        verbose_name = _("piece justificative")
        verbose_name_plural = _("pieces justificatives")
        ordering = ["uploaded_at"]

    def __str__(self):
        return f"{self.file.name} ({self.activity.code})"

    def clean(self):
        if self.size and self.size > self.TAILLE_MAX:
            raise ValidationError({"file": _("Fichier trop volumineux (5 Mo maximum).")})
        if self.mime_type and self.mime_type not in self.TYPES_AUTORISES:
            raise ValidationError({"file": _("Seuls les images et les PDF sont acceptes.")})


class ActivityParticipation(models.Model):
    """Participation a une activite : effectifs ou menages identifies."""

    activity = models.ForeignKey(
        Activity, on_delete=models.CASCADE, related_name="participations",
        verbose_name=_("activite"),
    )
    household = models.ForeignKey(
        "beneficiaries.Household", on_delete=models.CASCADE, null=True, blank=True,
        related_name="participations", verbose_name=_("menage"),
    )
    males_count = models.PositiveSmallIntegerField(_("hommes"), default=0)
    females_count = models.PositiveSmallIntegerField(_("femmes"), default=0)
    age_breakdown = models.JSONField(
        _("ventilation par age"), default=dict, blank=True,
        help_text=_("Cles : 0_5, 6_17, 18_59, 60_plus"),
    )

    class Meta:
        verbose_name = _("participation")
        verbose_name_plural = _("participations")
        constraints = [
            models.UniqueConstraint(
                fields=["activity", "household"], name="unique_participation_menage"
            )
        ]

    def __str__(self):
        cible = self.household.code if self.household else "effectifs anonymes"
        return f"{self.activity.code} — {cible}"