"""Cadre logique et indicateurs - paquetage P6 du cahier d'analyse."""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, Sum
from django.utils.translation import gettext_lazy as _


class LogFrameElement(models.Model):
    """Element du cadre logique d'un projet.

    Une seule classe reflexive porte les quatre niveaux : objectif general,
    objectif specifique, resultat attendu, activite. La hierarchie n'est
    donc pas figee dans le schema.
    """

    class Type(models.TextChoices):
        OBJECTIF_GENERAL = "og", _("Objectif general")
        OBJECTIF_SPECIFIQUE = "os", _("Objectif specifique")
        RESULTAT = "resultat", _("Resultat attendu")
        ACTIVITE = "activite", _("Activite")

    # Chaque niveau n'accepte qu'un parent du niveau immediatement superieur
    PARENT_ATTENDU = {
        Type.OBJECTIF_GENERAL: None,
        Type.OBJECTIF_SPECIFIQUE: Type.OBJECTIF_GENERAL,
        Type.RESULTAT: Type.OBJECTIF_SPECIFIQUE,
        Type.ACTIVITE: Type.RESULTAT,
    }

    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE,
        related_name="logframe", verbose_name=_("projet"),
    )
    type = models.CharField(_("niveau"), max_length=15, choices=Type.choices)
    code = models.CharField(_("code"), max_length=30)
    title = models.CharField(_("intitule"), max_length=300)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True,
        related_name="children", verbose_name=_("element parent"),
    )
    position = models.PositiveSmallIntegerField(_("ordre"), default=1)

    class Meta:
        verbose_name = _("element de cadre logique")
        verbose_name_plural = _("cadre logique")
        ordering = ["project", "position", "code"]
        constraints = [
            models.UniqueConstraint(fields=["project", "code"], name="unique_code_cadre_logique")
        ]

    def __str__(self):
        return f"{self.code} — {self.title[:60]}"

    def clean(self):
        attendu = self.PARENT_ATTENDU[self.type]
        if attendu is None and self.parent is not None:
            raise ValidationError({"parent": _("Un objectif general n'a pas de parent.")})
        if attendu is not None:
            if self.parent is None:
                raise ValidationError({"parent": _("Ce niveau exige un element parent.")})
            if self.parent.type != attendu:
                raise ValidationError(
                    {"parent": _("Le parent doit etre de niveau %s.") % attendu}
                )
            if self.parent.project_id != self.project_id:
                raise ValidationError(
                    {"parent": _("Le parent doit appartenir au meme projet.")}
                )


class Indicator(models.Model):
    """Indicateur mesurant l'atteinte d'un element du cadre logique."""

    class Unit(models.TextChoices):
        PERSONNES = "personnes", _("Personnes")
        MENAGES = "menages", _("Menages")
        POURCENTAGE = "pourcentage", _("Pourcentage")
        NOMBRE = "nombre", _("Nombre")
        SEANCES = "seances", _("Seances")

    class Frequency(models.TextChoices):
        MENSUELLE = "mensuelle", _("Mensuelle")
        TRIMESTRIELLE = "trimestrielle", _("Trimestrielle")
        SEMESTRIELLE = "semestrielle", _("Semestrielle")
        ANNUELLE = "annuelle", _("Annuelle")

    class Mode(models.TextChoices):
        CALCULE = "calcule", _("Calcule automatiquement")
        MANUEL = "manuel", _("Saisi manuellement")

    class Source(models.TextChoices):
        """Sources de calcul disponibles pour un indicateur automatique."""
        MENAGES_ATTEINTS = "menages_atteints", _("Menages rattaches au projet")
        INDIVIDUS_ATTEINTS = "individus_atteints", _("Individus des menages rattaches")
        ACTIVITES_VALIDEES = "activites_validees", _("Activites validees")
        PARTICIPANTS = "participants", _("Participants aux activites validees")
        FEMMES_ATTEINTES = "femmes_atteintes", _("Femmes parmi les individus atteints")

    element = models.ForeignKey(
        LogFrameElement, on_delete=models.CASCADE,
        related_name="indicators", verbose_name=_("element mesure"),
    )
    code = models.CharField(_("code"), max_length=30)
    title = models.CharField(_("intitule"), max_length=300)
    definition = models.TextField(_("definition"), blank=True)
    unit = models.CharField(_("unite"), max_length=15, choices=Unit.choices)

    baseline = models.DecimalField(
        _("valeur de reference"), max_digits=14, decimal_places=2, default=Decimal("0")
    )
    target = models.DecimalField(_("valeur cible"), max_digits=14, decimal_places=2)
    frequency = models.CharField(
        _("periodicite"), max_length=15, choices=Frequency.choices,
        default=Frequency.TRIMESTRIELLE,
    )
    verification_source = models.CharField(
        _("source de verification"), max_length=200, blank=True
    )
    computation_mode = models.CharField(
        _("mode de calcul"), max_length=10, choices=Mode.choices, default=Mode.MANUEL
    )
    computation_source = models.CharField(
        _("source de calcul"), max_length=25, choices=Source.choices, blank=True
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="indicators", verbose_name=_("responsable"),
    )

    class Meta:
        verbose_name = _("indicateur")
        verbose_name_plural = _("indicateurs")
        ordering = ["element__position", "code"]
        constraints = [
            models.CheckConstraint(condition=models.Q(target__gt=0), name="cible_positive")
        ]

    def __str__(self):
        return f"{self.code} — {self.title[:60]}"

    def clean(self):
        if self.computation_mode == self.Mode.CALCULE and not self.computation_source:
            raise ValidationError(
                {"computation_source": _("Un indicateur calcule exige une source.")}
            )

    @property
    def project(self):
        return self.element.project

    # ------------------------------------------------------------- valeurs
    @property
    def dernier_releve(self):
        return self.readings.filter(status=IndicatorReading.Status.VALIDE).order_by(
            "-period_end"
        ).first()

    @property
    def valeur_atteinte(self):
        releve = self.dernier_releve
        return releve.achieved_value if releve else Decimal("0")

    @property
    def taux_atteinte(self):
        """Part de la cible finale deja atteinte, en pourcentage."""
        if not self.target:
            return 0
        return round(float(self.valeur_atteinte) / float(self.target) * 100, 1)

    @property
    def taux_attendu(self):
        """Part de la cible normalement atteinte a ce stade du projet.

        Un projet a mi-parcours devrait afficher environ 50 % de sa cible.
        C'est cette valeur, et non la cible finale, qui sert de reference
        pour juger si un indicateur est en retard.
        """
        from django.utils import timezone

        projet = self.project
        aujourdhui = timezone.localdate()
        if aujourdhui <= projet.start_date:
            return 0
        if aujourdhui >= projet.end_date:
            return 100
        total = (projet.end_date - projet.start_date).days
        ecoule = (aujourdhui - projet.start_date).days
        return round(ecoule / total * 100, 1) if total else 0

    @property
    def statut_atteinte(self):
        """Code couleur du tableau de bord.

        Compare l'avancement reel a l'avancement attendu a cette date,
        et non a la cible finale.
        """
        attendu = self.taux_attendu
        if attendu <= 0:
            return "en_cours"          # le projet n'a pas encore demarre
        ratio = self.taux_atteinte / attendu
        if ratio >= 0.90:
            return "atteint"
        if ratio >= 0.60:
            return "en_cours"
        return "en_retard"

        from activities.models import Activity, ActivityParticipation
        from beneficiaries.models import HouseholdProject, Person

        projet = self.project
        source = self.computation_source

        if source == self.Source.MENAGES_ATTEINTS:
            return Decimal(HouseholdProject.objects.filter(project=projet).count())

        if source == self.Source.INDIVIDUS_ATTEINTS:
            return Decimal(Person.objects.filter(
                household__project_links__project=projet
            ).distinct().count())

        if source == self.Source.FEMMES_ATTEINTES:
            return Decimal(Person.objects.filter(
                household__project_links__project=projet, sex="F"
            ).distinct().count())

        if source == self.Source.ACTIVITES_VALIDEES:
            return Decimal(Activity.objects.filter(
                project=projet, status=Activity.Status.VALIDEE
            ).count())

        if source == self.Source.PARTICIPANTS:
            agregat = ActivityParticipation.objects.filter(
                activity__project=projet, activity__status=Activity.Status.VALIDEE
            ).aggregate(h=Sum("males_count"), f=Sum("females_count"))
            return Decimal((agregat["h"] or 0) + (agregat["f"] or 0))

        return None


class IndicatorDisaggregation(models.Model):
    """Dimension de ventilation declaree pour un indicateur."""

    class Dimension(models.TextChoices):
        SEXE = "sexe", _("Sexe")
        AGE = "age", _("Tranche d'age")
        ZONE = "zone", _("Zone geographique")
        VULNERABILITE = "vulnerabilite", _("Vulnerabilite")

    indicator = models.ForeignKey(
        Indicator, on_delete=models.CASCADE,
        related_name="disaggregations", verbose_name=_("indicateur"),
    )
    dimension = models.CharField(_("dimension"), max_length=15, choices=Dimension.choices)

    class Meta:
        verbose_name = _("desagregation")
        verbose_name_plural = _("desagregations")
        constraints = [
            models.UniqueConstraint(
                fields=["indicator", "dimension"], name="unique_desagregation"
            )
        ]

    def __str__(self):
        return f"{self.indicator.code} / {self.get_dimension_display()}"


class IndicatorReading(models.Model):
    """Releve periodique de la valeur atteinte par un indicateur."""

    class Status(models.TextChoices):
        BROUILLON = "brouillon", _("Brouillon")
        VALIDE = "valide", _("Valide")

    indicator = models.ForeignKey(
        Indicator, on_delete=models.CASCADE,
        related_name="readings", verbose_name=_("indicateur"),
    )
    period_start = models.DateField(_("debut de periode"))
    period_end = models.DateField(_("fin de periode"))
    achieved_value = models.DecimalField(
        _("valeur atteinte"), max_digits=14, decimal_places=2
    )
    breakdown = models.JSONField(
        _("ventilation"), default=dict, blank=True,
        help_text=_("Valeurs desagregees selon les dimensions declarees."),
    )
    comment = models.TextField(_("commentaire d'analyse"), blank=True)
    evidence = models.FileField(
        _("piece justificative"), upload_to="indicateurs/%Y/", blank=True, null=True
    )
    status = models.CharField(
        _("statut"), max_length=10, choices=Status.choices, default=Status.BROUILLON
    )
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="readings_entered", verbose_name=_("saisi par"),
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="readings_validated", verbose_name=_("valide par"),
    )
    created_at = models.DateTimeField(_("cree le"), auto_now_add=True)

    class Meta:
        verbose_name = _("releve d'indicateur")
        verbose_name_plural = _("releves d'indicateurs")
        ordering = ["-period_end"]
        constraints = [
            models.UniqueConstraint(
                fields=["indicator", "period_start", "period_end"],
                name="unique_releve_par_periode",
            ),
            models.CheckConstraint(
                condition=models.Q(period_end__gt=models.F("period_start")),
                name="periode_coherente",
            ),
            models.CheckConstraint(
                condition=models.Q(achieved_value__gte=0), name="valeur_non_negative"
            ),
        ]

    def __str__(self):
        return f"{self.indicator.code} — {self.period_end} : {self.achieved_value}"

    def clean(self):
        if self.indicator_id and self.status == self.Status.VALIDE:
            if (self.indicator.computation_mode == Indicator.Mode.MANUEL
                    and not self.evidence and not self.comment):
                raise ValidationError(_(
                    "Un releve manuel valide exige une piece justificative "
                    "ou un commentaire d'analyse."
                ))

    @property
    def taux_atteinte(self):
        cible = self.indicator.target
        if not cible:
            return 0
        return round(float(self.achieved_value) / float(cible) * 100, 1)