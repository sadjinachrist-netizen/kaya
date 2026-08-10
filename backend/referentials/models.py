"""Referentiels partages - paquetage P2 du cahier d'analyse."""
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class Organization(models.Model):
    """Identite de l'ONG. Instance unique (singleton fonctionnel)."""

    name = models.CharField(_("denomination"), max_length=200)
    acronym = models.CharField(_("sigle"), max_length=20, blank=True)
    address = models.CharField(_("adresse"), max_length=300, blank=True)
    phone = models.CharField(_("telephone"), max_length=30, blank=True)
    email = models.EmailField(_("email de contact"), blank=True)
    logo = models.ImageField(_("logo"), upload_to="organisation/", blank=True, null=True)
    legal_notice = models.TextField(_("mentions legales"), blank=True)

    class Meta:
        verbose_name = _("organisation")
        verbose_name_plural = _("organisation")

    def __str__(self):
        return self.acronym or self.name

    def save(self, *args, **kwargs):
        self.pk = 1  # force l'unicite de l'instance
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(_("L'organisation ne peut pas etre supprimee."))

    @classmethod
    def get_solo(cls):
        organisation, _cree = cls.objects.get_or_create(
            pk=1, defaults={"name": "Solidarite Developpement Togo", "acronym": "SDT"}
        )
        return organisation


class Zone(models.Model):
    """Decoupage administratif du Togo sur quatre niveaux."""

    class Level(models.TextChoices):
        REGION = "region", _("Region")
        PREFECTURE = "prefecture", _("Prefecture")
        CANTON = "canton", _("Canton")
        VILLAGE = "village", _("Village")

    # Chaque niveau n'accepte qu'un parent du niveau immediatement superieur
    PARENT_ATTENDU = {
        Level.REGION: None,
        Level.PREFECTURE: Level.REGION,
        Level.CANTON: Level.PREFECTURE,
        Level.VILLAGE: Level.CANTON,
    }

    code = models.SlugField(_("code"), max_length=50, unique=True)
    name = models.CharField(_("nom"), max_length=150)
    level = models.CharField(_("niveau"), max_length=15, choices=Level.choices)
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("zone parente"),
    )
    latitude = models.DecimalField(
        _("latitude"), max_digits=9, decimal_places=6, null=True, blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        _("longitude"), max_digits=9, decimal_places=6, null=True, blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("zone")
        verbose_name_plural = _("zones")
        ordering = ["level", "name"]
        indexes = [models.Index(fields=["level", "parent"])]

    def __str__(self):
        return self.name

    def clean(self):
        attendu = self.PARENT_ATTENDU[self.level]
        if attendu is None and self.parent is not None:
            raise ValidationError(
                {"parent": _("Une region ne peut pas avoir de zone parente.")}
            )
        if attendu is not None:
            if self.parent is None:
                raise ValidationError(
                    {"parent": _("Ce niveau exige une zone parente de niveau %s.") % attendu}
                )
            if self.parent.level != attendu:
                raise ValidationError(
                    {"parent": _("La zone parente doit etre de niveau %s.") % attendu}
                )

    @property
    def full_path(self):
        """Chemin hierarchique complet, du plus fin au plus large."""
        elements, courant = [], self
        while courant is not None:
            elements.append(courant.name)
            courant = courant.parent
        return " / ".join(elements)


class Sector(models.Model):
    """Secteur d'intervention, aligne sur la nomenclature humanitaire."""

    code = models.SlugField(_("code"), max_length=50, unique=True)
    label = models.CharField(_("intitule"), max_length=150)
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True,
        related_name="children", verbose_name=_("secteur parent"),
    )
    is_active = models.BooleanField(_("actif"), default=True)

    class Meta:
        verbose_name = _("secteur")
        verbose_name_plural = _("secteurs")
        ordering = ["label"]

    def __str__(self):
        return self.label


class Donor(models.Model):
    """Bailleur de fonds."""

    class Type(models.TextChoices):
        ONU = "onu", _("Agence des Nations Unies")
        BILATERAL = "bilateral", _("Cooperation bilaterale")
        UE = "ue", _("Union europeenne")
        FONDATION = "fondation", _("Fondation")
        PRIVE = "prive", _("Prive")
        AUTRE = "autre", _("Autre")

    name = models.CharField(_("denomination"), max_length=200)
    acronym = models.CharField(_("sigle"), max_length=30, blank=True)
    type = models.CharField(_("type"), max_length=15, choices=Type.choices)
    country = models.CharField(_("pays"), max_length=100, blank=True)
    contact_email = models.EmailField(_("email de contact"), blank=True)
    logo = models.ImageField(_("logo"), upload_to="bailleurs/", blank=True, null=True)
    visibility_rules = models.TextField(
        _("exigences de visibilite"), blank=True,
        help_text=_("Mentions imposees par le bailleur sur les documents produits."),
    )
    is_active = models.BooleanField(_("actif"), default=True)

    class Meta:
        verbose_name = _("bailleur")
        verbose_name_plural = _("bailleurs")
        ordering = ["name"]

    def __str__(self):
        return self.acronym or self.name


class Currency(models.Model):
    """Devise dans laquelle un montant peut etre libelle."""

    code = models.CharField(_("code ISO"), max_length=3, unique=True)
    name = models.CharField(_("nom"), max_length=60)
    symbol = models.CharField(_("symbole"), max_length=8, blank=True)
    is_base = models.BooleanField(
        _("devise de reference"), default=False,
        help_text=_("Devise dans laquelle les montants sont consolides."),
    )

    class Meta:
        verbose_name = _("devise")
        verbose_name_plural = _("devises")
        ordering = ["code"]

    def __str__(self):
        return self.code


class ExchangeRate(models.Model):
    """Taux de change historise entre deux devises."""

    currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, related_name="rates", verbose_name=_("devise")
    )
    base_currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, related_name="base_rates",
        verbose_name=_("devise de reference"),
    )
    rate = models.DecimalField(_("taux"), max_digits=18, decimal_places=8)
    effective_date = models.DateField(_("date d'application"))

    class Meta:
        verbose_name = _("taux de change")
        verbose_name_plural = _("taux de change")
        ordering = ["-effective_date", "currency"]
        constraints = [
            models.UniqueConstraint(
                fields=["currency", "base_currency", "effective_date"],
                name="unique_taux_par_date",
            ),
            models.CheckConstraint(condition=models.Q(rate__gt=0), name="taux_positif"),
        ]

    def __str__(self):
        return f"1 {self.currency.code} = {self.rate} {self.base_currency.code} ({self.effective_date})"