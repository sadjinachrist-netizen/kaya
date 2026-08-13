"""Notifications et preferences - paquetage P6 du cahier d'analyse."""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class EventType(models.TextChoices):
    """Evenements pouvant declencher une notification."""

    ACTIVITE_SOUMISE = "activite_soumise", _("Activite soumise a validation")
    ACTIVITE_VALIDEE = "activite_validee", _("Activite validee")
    ACTIVITE_REJETEE = "activite_rejetee", _("Activite rejetee")
    DOUBLON_DETECTE = "doublon_detecte", _("Doublon de menage detecte")
    ECHEANCE_PROCHE = "echeance_proche", _("Echeance bailleur proche")
    DEPASSEMENT_BUDGET = "depassement_budget", _("Depassement de ligne budgetaire")
    INDICATEUR_EN_RETARD = "indicateur_en_retard", _("Indicateur en retard")
    COMPTE_MODIFIE = "compte_modifie", _("Compte ou role modifie")


class Notification(models.Model):
    class Channel(models.TextChoices):
        APPLICATION = "application", _("Dans l'application")
        EMAIL = "email", _("Par email")

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="notifications", verbose_name=_("destinataire"),
    )
    event_type = models.CharField(_("evenement"), max_length=30, choices=EventType.choices)
    subject = models.CharField(_("objet"), max_length=200)
    message = models.TextField(_("message"))
    channel = models.CharField(
        _("canal"), max_length=15, choices=Channel.choices, default=Channel.APPLICATION
    )

    # Permet au front de proposer un lien vers l'objet concerne
    object_type = models.CharField(_("type d'objet"), max_length=50, blank=True)
    object_id = models.CharField(_("identifiant de l'objet"), max_length=50, blank=True)

    is_read = models.BooleanField(_("lue"), default=False)
    read_at = models.DateTimeField(_("lue le"), null=True, blank=True)
    sent_at = models.DateTimeField(_("envoyee le"), auto_now_add=True)

    class Meta:
        verbose_name = _("notification")
        verbose_name_plural = _("notifications")
        ordering = ["-sent_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "-sent_at"]),
            models.Index(fields=["event_type", "-sent_at"]),
        ]

    def __str__(self):
        return f"{self.recipient.username} — {self.subject}"


class NotificationPreference(models.Model):
    """Choix de l'utilisateur pour un type d'evenement.

    L'absence de preference vaut acceptation : par defaut on notifie
    dans l'application, sans email.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="notification_preferences", verbose_name=_("utilisateur"),
    )
    event_type = models.CharField(_("evenement"), max_length=30, choices=EventType.choices)
    in_app = models.BooleanField(_("dans l'application"), default=True)
    by_email = models.BooleanField(_("par email"), default=False)

    class Meta:
        verbose_name = _("preference de notification")
        verbose_name_plural = _("preferences de notification")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "event_type"], name="unique_preference_par_evenement"
            )
        ]

    def __str__(self):
        return f"{self.user.username} — {self.get_event_type_display()}"