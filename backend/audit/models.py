"""Journal d'audit - paquetage P1 Securite et habilitations.

Le journal est en ecriture seule : aucune entree ne peut etre modifiee
ni supprimee, y compris par un administrateur (exigence du cahier des charges).
"""
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import models
from django.utils.translation import gettext_lazy as _


class AuditLogQuerySet(models.QuerySet):
    """Interdit toute modification ou suppression en masse."""

    def update(self, **kwargs):
        raise PermissionDenied(_("Le journal d'audit est en ecriture seule."))

    def delete(self):
        raise PermissionDenied(_("Le journal d'audit est en ecriture seule."))


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATION = "creation", _("Creation")
        MODIFICATION = "modification", _("Modification")
        SUPPRESSION = "suppression", _("Suppression")
        CONSULTATION = "consultation", _("Consultation de donnee sensible")
        EXPORT = "export", _("Export de donnees")
        CONNEXION = "connexion", _("Connexion")
        DECONNEXION = "deconnexion", _("Deconnexion")
        ACCES_REFUSE = "acces_refuse", _("Acces refuse")

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_entries",
        verbose_name=_("auteur"),
    )
    action = models.CharField(_("action"), max_length=20, choices=Action.choices)
    object_type = models.CharField(_("type d'objet"), max_length=100, blank=True)
    object_id = models.CharField(_("identifiant de l'objet"), max_length=50, blank=True)
    object_label = models.CharField(_("designation"), max_length=255, blank=True)

    old_value = models.JSONField(_("valeur avant"), null=True, blank=True)
    new_value = models.JSONField(_("valeur apres"), null=True, blank=True)

    ip_address = models.GenericIPAddressField(_("adresse IP"), null=True, blank=True)
    user_agent = models.CharField(_("navigateur"), max_length=255, blank=True)
    detail = models.CharField(_("detail"), max_length=255, blank=True)

    timestamp = models.DateTimeField(_("horodatage"), auto_now_add=True, db_index=True)

    objects = AuditLogQuerySet.as_manager()

    class Meta:
        verbose_name = _("entree du journal d'audit")
        verbose_name_plural = _("journal d'audit")
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["object_type", "object_id"]),
            models.Index(fields=["actor", "-timestamp"]),
            models.Index(fields=["action", "-timestamp"]),
        ]

    def __str__(self):
        auteur = self.actor.username if self.actor else "systeme"
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {auteur} — {self.action} {self.object_type}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise PermissionDenied(
                _("Une entree du journal d'audit ne peut pas etre modifiee.")
            )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionDenied(
            _("Une entree du journal d'audit ne peut pas etre supprimee.")
        )