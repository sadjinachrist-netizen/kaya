"""Roles et permissions - paquetage P1 Securite et habilitations."""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone


class Permission(models.Model):
    """Action elementaire autorisable, independante de tout ecran."""

    class Module(models.TextChoices):
        SECURITE = "securite", _("Securite et administration")
        PROJETS = "projets", _("Projets")
        FINANCEMENTS = "financements", _("Financements et budget")
        BENEFICIAIRES = "beneficiaires", _("Beneficiaires")
        ACTIVITES = "activites", _("Activites terrain")
        SUIVI = "suivi", _("Suivi-evaluation")
        RESTITUTION = "restitution", _("Restitution")

    code = models.CharField(
        _("code"),
        max_length=100,
        unique=True,
        help_text=_("Format objet.action, par exemple activite.valider"),
    )
    module = models.CharField(_("module"), max_length=30, choices=Module.choices)
    label = models.CharField(_("intitule"), max_length=200)

    class Meta:
        verbose_name = _("permission")
        verbose_name_plural = _("permissions")
        ordering = ["module", "code"]

    def __str__(self):
        return self.code


class Role(models.Model):
    """Regroupement de permissions attribuable a des utilisateurs."""

    code = models.SlugField(_("code"), max_length=50, unique=True)
    label = models.CharField(_("intitule"), max_length=100)
    description = models.TextField(_("description"), blank=True)

    # Regle SEC-06 : certains roles ne peuvent pas desactiver le second facteur
    requires_mfa = models.BooleanField(_("second facteur obligatoire"), default=False)

    permissions = models.ManyToManyField(
        Permission,
        through="RolePermission",
        related_name="roles",
        blank=True,
        verbose_name=_("permissions"),
    )
    users = models.ManyToManyField(
        "accounts.User",
        related_name="roles",
        blank=True,
        verbose_name=_("utilisateurs"),
    )

    class Meta:
        verbose_name = _("role")
        verbose_name_plural = _("roles")
        ordering = ["label"]

    def __str__(self):
        return self.label

class RolePermission(models.Model):
    """Attribution d'une permission a un role, avec son etendue."""

    class Scope(models.TextChoices):
        GLOBAL = "global", _("Toutes les donnees du systeme")
        PORTEE = "portee", _("Limitee a la portee de l'utilisateur")

    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name="grants", verbose_name=_("role")
    )
    permission = models.ForeignKey(
        Permission, on_delete=models.CASCADE, related_name="grants", verbose_name=_("permission")
    )
    scope = models.CharField(
        _("etendue"), max_length=10, choices=Scope.choices, default=Scope.PORTEE
    )

    class Meta:
        verbose_name = _("attribution de permission")
        verbose_name_plural = _("attributions de permissions")
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"], name="unique_role_permission"
            )
        ]
        ordering = ["role", "permission"]

    def __str__(self):
        return f"{self.role.code} → {self.permission.code} ({self.scope})"




class UserScope(models.Model):
    """Perimetre de donnees accessible a un utilisateur.

    Troisieme dimension du modele d'habilitation : la permission dit
    *ce que* l'utilisateur peut faire, la portee dit *sur quoi*.
    """

    class Type(models.TextChoices):
        GLOBAL = "global", _("Toutes les donnees")
        PROJECT = "project", _("Un projet")
        ZONE = "zone", _("Une zone geographique")

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="scopes",
        verbose_name=_("utilisateur"),
    )
    scope_type = models.CharField(_("type de portee"), max_length=10, choices=Type.choices)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="scopes",
        verbose_name=_("projet"),
    )
    zone = models.ForeignKey(
        "referentials.Zone",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="scopes",
        verbose_name=_("zone"),
    )

    # Delegation temporaire : une fin est obligatoire (regle 8.1)
    start_date = models.DateField(_("debut de validite"), null=True, blank=True)
    end_date = models.DateField(_("fin de validite"), null=True, blank=True)

    class Meta:
        verbose_name = _("portee")
        verbose_name_plural = _("portees")
        ordering = ["user", "scope_type"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(scope_type="global", project__isnull=True, zone__isnull=True)
                    | models.Q(scope_type="project", project__isnull=False, zone__isnull=True)
                    | models.Q(scope_type="zone", zone__isnull=False, project__isnull=True)
                ),
                name="portee_coherente",
            )
        ]

    def __str__(self):
        cible = self.project or self.zone or "tout le systeme"
        return f"{self.user.username} → {cible}"

    def clean(self):
        if self.scope_type == self.Type.PROJECT and self.project is None:
            raise ValidationError({"project": _("Un projet doit etre designe.")})
        if self.scope_type == self.Type.ZONE and self.zone is None:
            raise ValidationError({"zone": _("Une zone doit etre designee.")})
        if self.scope_type == self.Type.GLOBAL and (self.project or self.zone):
            raise ValidationError(_("Une portee globale ne designe ni projet ni zone."))
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": _("La fin ne peut preceder le debut.")})

    @property
    def is_active(self):
        aujourdhui = timezone.localdate()
        if self.start_date and self.start_date > aujourdhui:
            return False
        if self.end_date and self.end_date < aujourdhui:
            return False
        return True