"""Financements et budget - paquetage P4 du cahier d'analyse."""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from referentials.models import Currency, Donor


class Grant(models.Model):
    """Convention de financement conclue avec un bailleur."""

    class Status(models.TextChoices):
        INSTRUCTION = "instruction", _("En instruction")
        SIGNE = "signe", _("Signe")
        CLOS = "clos", _("Clos")

    contract_number = models.CharField(_("numero de contrat"), max_length=60, unique=True)
    title = models.CharField(_("intitule"), max_length=200)
    donor = models.ForeignKey(
        Donor, on_delete=models.PROTECT, related_name="grants", verbose_name=_("bailleur")
    )
    amount = models.DecimalField(_("montant accorde"), max_digits=14, decimal_places=2)
    currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, related_name="grants", verbose_name=_("devise")
    )
    signature_date = models.DateField(_("date de signature"), null=True, blank=True)
    eligibility_start = models.DateField(_("debut d'eligibilite des depenses"))
    eligibility_end = models.DateField(_("fin d'eligibilite des depenses"))
    document = models.FileField(
        _("convention signee"), upload_to="conventions/%Y/", blank=True, null=True
    )
    status = models.CharField(
        _("statut"), max_length=15, choices=Status.choices, default=Status.INSTRUCTION
    )
    created_at = models.DateTimeField(_("cree le"), auto_now_add=True)

    class Meta:
        verbose_name = _("financement")
        verbose_name_plural = _("financements")
        ordering = ["-signature_date", "contract_number"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(eligibility_end__gt=models.F("eligibility_start")),
                name="eligibilite_coherente",
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="montant_financement_positif"
            ),
        ]

    def __str__(self):
        return f"{self.contract_number} — {self.donor}"

    def clean(self):
        if self.eligibility_start and self.eligibility_end:
            if self.eligibility_end <= self.eligibility_start:
                raise ValidationError(
                    {"eligibility_end": _("La fin d'eligibilite doit suivre le debut.")}
                )

    # ------------------------------------------------------ suivi financier
    @property
    def quote_part_totale(self):
        """Somme des quotes-parts attribuees aux projets, en pourcentage."""
        total = self.project_links.aggregate(t=Sum("share_percent"))["t"]
        return total or Decimal("0")

    @property
    def budget_total(self):
        """Somme des lignes budgetaires de premier niveau."""
        total = self.budget_lines.filter(parent__isnull=True).aggregate(
            t=Sum("budgeted_amount")
        )["t"]
        return total or Decimal("0")

    @property
    def montant_depense(self):
        total = Expense.objects.filter(
            budget_line__grant=self, status=Expense.Status.VALIDEE
        ).aggregate(t=Sum("amount"))["t"]
        return total or Decimal("0")

    @property
    def montant_disponible(self):
        return self.amount - self.montant_depense

    @property
    def taux_consommation(self):
        """Part du financement deja depensee, en pourcentage."""
        if not self.amount:
            return 0
        return round(self.montant_depense / self.amount * 100, 1)

    @property
    def taux_temps_ecoule(self):
        """Part de la periode d'eligibilite deja ecoulee, en pourcentage."""
        aujourdhui = timezone.localdate()
        if aujourdhui <= self.eligibility_start:
            return 0
        if aujourdhui >= self.eligibility_end:
            return 100
        total = (self.eligibility_end - self.eligibility_start).days
        ecoule = (aujourdhui - self.eligibility_start).days
        return round(ecoule / total * 100, 1) if total else 0

    @property
    def ecart_rythme(self):
        """Ecart entre consommation et temps ecoule, en points.

        Negatif = sous-consommation, positif = surconsommation.
        Au-dela de 20 points en valeur absolue, une alerte est levee
        (exigence du cahier des charges).
        """
        return round(float(self.taux_consommation) - float(self.taux_temps_ecoule), 1)

    @property
    def alerte_rythme(self):
        ecart = self.ecart_rythme
        if ecart < -20:
            return "sous_consommation"
        if ecart > 20:
            return "sur_consommation"
        return None


class GrantProject(models.Model):
    """Rattachement d'un financement a un projet, avec sa quote-part."""

    grant = models.ForeignKey(
        Grant, on_delete=models.CASCADE, related_name="project_links",
        verbose_name=_("financement"),
    )
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="grant_links",
        verbose_name=_("projet"),
    )
    share_percent = models.DecimalField(
        _("quote-part (%)"), max_digits=5, decimal_places=2, default=Decimal("100.00")
    )

    class Meta:
        verbose_name = _("financement de projet")
        verbose_name_plural = _("financements de projets")
        constraints = [
            models.UniqueConstraint(
                fields=["grant", "project"], name="unique_financement_projet"
            ),
            models.CheckConstraint(
                condition=models.Q(share_percent__gt=0, share_percent__lte=100),
                name="quote_part_valide",
            ),
        ]

    def __str__(self):
        return f"{self.grant.contract_number} → {self.project.code} ({self.share_percent} %)"

    def clean(self):
        """La somme des quotes-parts d'un financement ne peut exceder 100 %."""
        if self.grant_id is None:
            return
        autres = GrantProject.objects.filter(grant=self.grant).exclude(pk=self.pk)
        deja = autres.aggregate(t=Sum("share_percent"))["t"] or Decimal("0")
        if deja + (self.share_percent or Decimal("0")) > Decimal("100"):
            raise ValidationError(
                {"share_percent": _(
                    "Quote-part excessive : %(reste)s %% encore disponibles sur ce financement."
                ) % {"reste": Decimal("100") - deja}}
            )


class BudgetLine(models.Model):
    """Ligne budgetaire hierarchique rattachee a un financement."""

    class Category(models.TextChoices):
        PERSONNEL = "personnel", _("Personnel")
        EQUIPEMENT = "equipement", _("Equipement")
        ACTIVITES = "activites", _("Activites")
        TRANSPORT = "transport", _("Transport")
        FONCTIONNEMENT = "fonctionnement", _("Fonctionnement")
        ADMINISTRATIF = "administratif", _("Frais administratifs")

    grant = models.ForeignKey(
        Grant, on_delete=models.CASCADE, related_name="budget_lines",
        verbose_name=_("financement"),
    )
    code = models.CharField(_("code"), max_length=30)
    label = models.CharField(_("intitule"), max_length=200)
    category = models.CharField(_("categorie"), max_length=20, choices=Category.choices)
    budgeted_amount = models.DecimalField(
        _("montant budgete"), max_digits=14, decimal_places=2
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True,
        related_name="children", verbose_name=_("ligne parente"),
    )

    class Meta:
        verbose_name = _("ligne budgetaire")
        verbose_name_plural = _("lignes budgetaires")
        ordering = ["grant", "code"]
        constraints = [
            models.UniqueConstraint(fields=["grant", "code"], name="unique_ligne_par_financement"),
            models.CheckConstraint(
                condition=models.Q(budgeted_amount__gte=0), name="montant_ligne_positif"
            ),
        ]

    def __str__(self):
        return f"{self.code} — {self.label}"

    def clean(self):
        if self.parent and self.parent.grant_id != self.grant_id:
            raise ValidationError(
                {"parent": _("La ligne parente doit appartenir au meme financement.")}
            )
        if self.parent and self.parent_id == self.pk:
            raise ValidationError({"parent": _("Une ligne ne peut pas etre sa propre parente.")})

    @property
    def montant_depense(self):
        total = self.expenses.filter(status=Expense.Status.VALIDEE).aggregate(
            t=Sum("amount")
        )["t"]
        return total or Decimal("0")

    @property
    def montant_disponible(self):
        return self.budgeted_amount - self.montant_depense

    @property
    def taux_consommation(self):
        if not self.budgeted_amount:
            return 0
        return round(self.montant_depense / self.budgeted_amount * 100, 1)

    @property
    def est_depassee(self):
        return self.montant_depense > self.budgeted_amount


class Expense(models.Model):
    """Depense imputee sur une ligne budgetaire."""

    class Status(models.TextChoices):
        SAISIE = "saisie", _("Saisie")
        VALIDEE = "validee", _("Validee")
        REJETEE = "rejetee", _("Rejetee")

    budget_line = models.ForeignKey(
        BudgetLine, on_delete=models.PROTECT, related_name="expenses",
        verbose_name=_("ligne budgetaire"),
    )
    project = models.ForeignKey(
        "projects.Project", on_delete=models.PROTECT, related_name="expenses",
        verbose_name=_("projet"),
    )
    label = models.CharField(_("objet de la depense"), max_length=200)
    amount = models.DecimalField(_("montant"), max_digits=14, decimal_places=2)
    currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, related_name="expenses", verbose_name=_("devise")
    )
    expense_date = models.DateField(_("date de la depense"))
    receipt = models.FileField(
        _("piece justificative"), upload_to="depenses/%Y/%m/", blank=True, null=True
    )
    status = models.CharField(
        _("statut"), max_length=10, choices=Status.choices, default=Status.SAISIE
    )
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="expenses_entered", verbose_name=_("saisie par"),
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="expenses_validated", verbose_name=_("validee par"),
    )
    created_at = models.DateTimeField(_("creee le"), auto_now_add=True)

    class Meta:
        verbose_name = _("depense")
        verbose_name_plural = _("depenses")
        ordering = ["-expense_date"]
        indexes = [
            models.Index(fields=["budget_line", "status"]),
            models.Index(fields=["project", "-expense_date"]),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="depense_positive")
        ]

    def __str__(self):
        return f"{self.label} — {self.amount} {self.currency.code}"

    def clean(self):
        """Une depense doit tomber dans la periode d'eligibilite du financement."""
        if self.budget_line_id is None or self.expense_date is None:
            return
        financement = self.budget_line.grant
        if not (financement.eligibility_start <= self.expense_date <= financement.eligibility_end):
            raise ValidationError({"expense_date": _(
                "Depense hors periode d'eligibilite du financement "
                "(%(debut)s au %(fin)s)."
            ) % {"debut": financement.eligibility_start, "fin": financement.eligibility_end}})


class ReportDeadline(models.Model):
    """Echeance de rapport due au bailleur. Composition avec Grant."""

    class Type(models.TextChoices):
        NARRATIF = "narratif", _("Rapport narratif")
        FINANCIER = "financier", _("Rapport financier")
        FINAL = "final", _("Rapport final")

    class Status(models.TextChoices):
        A_FAIRE = "a_faire", _("A faire")
        EN_COURS = "en_cours", _("En cours")
        SOUMIS = "soumis", _("Soumis")
        ACCEPTE = "accepte", _("Accepte")

    grant = models.ForeignKey(
        Grant, on_delete=models.CASCADE, related_name="deadlines",
        verbose_name=_("financement"),
    )
    type = models.CharField(_("type"), max_length=15, choices=Type.choices)
    due_date = models.DateField(_("date d'echeance"))
    status = models.CharField(
        _("statut"), max_length=10, choices=Status.choices, default=Status.A_FAIRE
    )
    submitted_at = models.DateTimeField(_("soumis le"), null=True, blank=True)
    document = models.FileField(
        _("document transmis"), upload_to="rapports-bailleurs/%Y/", blank=True, null=True
    )

    class Meta:
        verbose_name = _("echeance de rapportage")
        verbose_name_plural = _("echeancier de rapportage")
        ordering = ["due_date"]

    def __str__(self):
        return f"{self.get_type_display()} — {self.due_date} ({self.grant.contract_number})"

    @property
    def jours_restants(self):
        return (self.due_date - timezone.localdate()).days

    @property
    def alerte(self):
        """Alerte a J-30, J-15 et J-7 (exigence du cahier des charges)."""
        if self.status in (self.Status.SOUMIS, self.Status.ACCEPTE):
            return None
        restants = self.jours_restants
        if restants < 0:
            return "en_retard"
        if restants <= 7:
            return "j7"
        if restants <= 15:
            return "j15"
        if restants <= 30:
            return "j30"
        return None


class Installment(models.Model):
    """Tranche de versement attendue au titre d'un financement."""

    class Status(models.TextChoices):
        ATTENDU = "attendu", _("Attendu")
        RECU = "recu", _("Recu")
        ANNULE = "annule", _("Annule")

    grant = models.ForeignKey(
        Grant, on_delete=models.CASCADE, related_name="installments",
        verbose_name=_("financement"),
    )
    amount = models.DecimalField(_("montant"), max_digits=14, decimal_places=2)
    expected_date = models.DateField(_("date prevue"))
    received_date = models.DateField(_("date de reception"), null=True, blank=True)
    status = models.CharField(
        _("statut"), max_length=10, choices=Status.choices, default=Status.ATTENDU
    )

    class Meta:
        verbose_name = _("tranche de versement")
        verbose_name_plural = _("tranches de versement")
        ordering = ["expected_date"]

    def __str__(self):
        return f"{self.amount} {self.grant.currency.code} — {self.expected_date}"