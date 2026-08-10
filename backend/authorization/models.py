"""Roles et permissions - paquetage P1 Securite et habilitations."""
from django.db import models
from django.utils.translation import gettext_lazy as _


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