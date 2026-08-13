"""Emission des notifications."""
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import EventType, Notification, NotificationPreference


def _preference(utilisateur, evenement):
    return NotificationPreference.objects.filter(
        user=utilisateur, event_type=evenement
    ).first()


def notifier(destinataires, evenement, sujet, message, *, obj=None,
             object_type="", object_id=""):
    """Cree une notification pour chaque destinataire.

    Respecte les preferences de l'utilisateur : une preference absente
    vaut acceptation dans l'application, sans email.
    """
    if obj is not None:
        object_type = object_type or obj.__class__.__name__
        object_id = object_id or str(obj.pk)

    if not isinstance(destinataires, (list, tuple, set)):
        destinataires = [destinataires]

    creees = []
    for utilisateur in destinataires:
        if utilisateur is None:
            continue
        preference = _preference(utilisateur, evenement)
        dans_application = preference.in_app if preference else True
        par_email = preference.by_email if preference else False

        if dans_application:
            creees.append(Notification.objects.create(
                recipient=utilisateur,
                event_type=evenement,
                subject=sujet[:200],
                message=message,
                channel=Notification.Channel.APPLICATION,
                object_type=object_type,
                object_id=str(object_id),
            ))

        if par_email and utilisateur.email:
            send_mail(
                subject=f"[Kaya] {sujet}",
                message=message,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "kaya@localhost"),
                recipient_list=[utilisateur.email],
                fail_silently=True,
            )
            creees.append(Notification.objects.create(
                recipient=utilisateur,
                event_type=evenement,
                subject=sujet[:200],
                message=message,
                channel=Notification.Channel.EMAIL,
                object_type=object_type,
                object_id=str(object_id),
            ))
    return creees


# ------------------------------------------------------------ destinataires
def valideurs_du_projet(projet):
    """Superviseurs et chef d'un projet, destinataires des demandes de validation."""
    from accounts.models import User
    from projects.models import TeamMember

    aujourdhui = timezone.localdate()
    superviseurs = User.objects.filter(
        project_memberships__project=projet,
        project_memberships__project_role=TeamMember.ProjectRole.SUPERVISEUR,
        project_memberships__start_date__lte=aujourdhui,
        is_active=True,
    ).distinct()
    return list(superviseurs) + ([projet.manager] if projet.manager else [])


# --------------------------------------------------- evenements du domaine
def activite_soumise(activite):
    return notifier(
        valideurs_du_projet(activite.project),
        EventType.ACTIVITE_SOUMISE,
        f"Activite {activite.code} a valider",
        f"{activite.agent.full_name} a soumis une activite du type "
        f"« {activite.get_type_display()} » realisee le {activite.activity_date} "
        f"sur le projet {activite.project.code}.",
        obj=activite,
    )


def activite_statuee(activite, validee):
    if validee:
        sujet = f"Activite {activite.code} validee"
        corps = (f"Votre saisie du {activite.activity_date} a ete validee par "
                 f"{activite.validated_by.full_name if activite.validated_by else 'un superviseur'}.")
        evenement = EventType.ACTIVITE_VALIDEE
    else:
        sujet = f"Activite {activite.code} rejetee"
        corps = (f"Votre saisie du {activite.activity_date} a ete rejetee.\n\n"
                 f"Motif : {activite.rejection_reason}\n\n"
                 f"Vous pouvez la corriger et la soumettre a nouveau.")
        evenement = EventType.ACTIVITE_REJETEE
    return notifier(activite.agent, evenement, sujet, corps, obj=activite)


def doublon_detecte(candidat):
    from projects.models import Project

    projets = Project.objects.filter(
        household_links__household=candidat.household_b
    ).distinct()
    destinataires = []
    for projet in projets:
        destinataires.extend(valideurs_du_projet(projet))
    return notifier(
        set(destinataires),
        EventType.DOUBLON_DETECTE,
        f"Doublon possible : {candidat.household_b.code}",
        f"Le menage {candidat.household_b.code} ressemble a {candidat.household_a.code} "
        f"(score {candidat.score}). Un arbitrage est necessaire.",
        obj=candidat,
    )