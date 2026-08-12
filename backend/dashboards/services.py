"""Agregations des tableaux de bord, un par role."""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone

from activities.models import Activity
from authorization.scopes import projets_accessibles
from beneficiaries.models import DuplicateCandidate, Household, Person
from funding.models import Expense, Grant, ReportDeadline
from monitoring.models import Indicator
from projects.models import Project


# ---------------------------------------------------------------- outils
def _sadd(menages):
    """Effectifs desagreges par sexe et tranche d'age sur un ensemble de menages."""
    personnes = Person.objects.filter(household__in=menages)
    aujourdhui = timezone.localdate()
    tranches = {"0_5": [0, 0], "6_17": [0, 0], "18_59": [0, 0], "60_plus": [0, 0]}
    for sexe, naissance, age_estime in personnes.values_list(
        "sex", "birth_date", "estimated_age"
    ):
        if naissance:
            age = aujourdhui.year - naissance.year - (
                (aujourdhui.month, aujourdhui.day) < (naissance.month, naissance.day)
            )
        else:
            age = age_estime
        if age is None:
            continue
        cle = "0_5" if age <= 5 else "6_17" if age <= 17 else "18_59" if age <= 59 else "60_plus"
        tranches[cle][0 if sexe == "M" else 1] += 1
    return {c: {"hommes": v[0], "femmes": v[1], "total": v[0] + v[1]}
            for c, v in tranches.items()}


def _menages_du_perimetre(projets):
    """Menages rattaches aux projets, hors doublons confirmes."""
    return Household.objects.filter(
        project_links__project__in=projets
    ).exclude(validation_status=Household.ValidationStatus.DOUBLON).distinct()


# ------------------------------------------------------------ agent terrain
def tableau_agent(user):
    projets = projets_accessibles(user)
    mes_activites = Activity.objects.filter(agent=user)
    debut_mois = timezone.localdate().replace(day=1)

    par_statut = dict(
        mes_activites.values_list("status").annotate(n=Count("id"))
    )
    rejetees = mes_activites.filter(status=Activity.Status.REJETEE).select_related(
        "project"
    ).order_by("-validated_at")[:5]

    return {
        "role": "agent_terrain",
        "tuiles": {
            "a_corriger": par_statut.get(Activity.Status.REJETEE, 0),
            "brouillons": par_statut.get(Activity.Status.BROUILLON, 0),
            "en_attente_validation": par_statut.get(Activity.Status.SOUMISE, 0),
            "validees": par_statut.get(Activity.Status.VALIDEE, 0),
        },
        "collecte_du_mois": {
            "menages": Household.objects.filter(
                registered_by=user, registered_at__date__gte=debut_mois
            ).count(),
            "activites": mes_activites.filter(activity_date__gte=debut_mois).count(),
        },
        "a_corriger": [
            {
                "id": a.id, "code": a.code, "projet": a.project.code,
                "date": a.activity_date, "motif": a.rejection_reason,
            }
            for a in rejetees
        ],
        "mes_projets": list(
            projets.values("id", "code", "title", "status")[:10]
        ),
    }


# --------------------------------------------------------- superviseur
def tableau_superviseur(user):
    projets = projets_accessibles(user)
    a_valider = Activity.objects.filter(
        project__in=projets, status=Activity.Status.SOUMISE
    ).select_related("project", "agent", "zone").order_by("submitted_at")

    avec_alertes = [a for a in a_valider if a.alertes_qualite]
    menages = _menages_du_perimetre(projets)

    return {
        "role": "superviseur",
        "tuiles": {
            "activites_a_valider": a_valider.count(),
            "alertes_qualite": len(avec_alertes),
            "doublons_a_arbitrer": DuplicateCandidate.objects.filter(
                status=DuplicateCandidate.Status.A_ARBITRER,
                household_a__in=menages,
            ).count(),
            "menages_a_valider": menages.filter(
                validation_status=Household.ValidationStatus.A_VALIDER
            ).count(),
        },
        "file_validation": [
            {
                "id": a.id, "code": a.code, "projet": a.project.code,
                "type": a.get_type_display(), "date": a.activity_date,
                "zone": a.zone.name, "agent": a.agent.full_name,
                "alertes": a.alertes_qualite,
            }
            for a in a_valider[:15]
        ],
        "par_agent": list(
            Activity.objects.filter(project__in=projets)
            .values("agent__username", "agent__first_name", "agent__last_name")
            .annotate(
                total=Count("id"),
                validees=Count("id", filter=Q(status=Activity.Status.VALIDEE)),
                rejetees=Count("id", filter=Q(status=Activity.Status.REJETEE)),
            )
            .order_by("-total")[:10]
        ),
    }


# --------------------------------------------------------- chef de projet
def tableau_projet(user, projet=None):
    projets = projets_accessibles(user)
    if projet is not None:
        projets = projets.filter(pk=projet.pk)

    menages = _menages_du_perimetre(projets)
    indicateurs = Indicator.objects.filter(element__project__in=projets).select_related(
        "element__project"
    )
    repartition = {"atteint": 0, "en_cours": 0, "en_retard": 0}
    detail_indicateurs = []
    for indicateur in indicateurs:
        repartition[indicateur.statut_atteinte] += 1
        detail_indicateurs.append({
            "id": indicateur.id, "code": indicateur.code, "titre": indicateur.title,
            "unite": indicateur.unit, "cible": str(indicateur.target),
            "atteint": str(indicateur.valeur_atteinte),
            "taux": indicateur.taux_atteinte, "attendu": indicateur.taux_attendu,
            "statut": indicateur.statut_atteinte,
        })

    financements = Grant.objects.filter(project_links__project__in=projets).distinct()
    echeances = ReportDeadline.objects.filter(
        grant__in=financements,
        status__in=[ReportDeadline.Status.A_FAIRE, ReportDeadline.Status.EN_COURS],
        due_date__lte=timezone.localdate() + timedelta(days=30),
    ).select_related("grant__donor").order_by("due_date")

    return {
        "role": "chef_projet",
        "tuiles": {
            "projets": projets.count(),
            "beneficiaires": menages.count(),
            "individus": Person.objects.filter(household__in=menages).count(),
            "activites_a_valider": Activity.objects.filter(
                project__in=projets, status=Activity.Status.SOUMISE
            ).count(),
        },
        "indicateurs": {
            "repartition": repartition,
            "detail": sorted(detail_indicateurs, key=lambda i: i["taux"])[:12],
        },
        "budget": [
            {
                "convention": g.contract_number, "bailleur": str(g.donor),
                "montant": str(g.amount), "devise": g.currency.code,
                "consomme": g.taux_consommation, "temps_ecoule": g.taux_temps_ecoule,
                "ecart": g.ecart_rythme, "alerte": g.alerte_rythme,
            }
            for g in financements.select_related("donor", "currency")
        ],
        "sadd": _sadd(menages),
        "echeances": [
            {
                "id": e.id, "type": e.get_type_display(),
                "convention": e.grant.contract_number,
                "echeance": e.due_date, "jours_restants": e.jours_restants,
                "alerte": e.alerte,
            }
            for e in echeances[:8]
        ],
    }


# ------------------------------------------------------- suivi-evaluation
def tableau_suivi_evaluation(user):
    projets = projets_accessibles(user)
    menages = _menages_du_perimetre(projets)
    indicateurs = Indicator.objects.filter(element__project__in=projets).select_related(
        "element__project"
    )

    repartition = {"atteint": 0, "en_cours": 0, "en_retard": 0}
    par_projet = {}
    for indicateur in indicateurs:
        statut = indicateur.statut_atteinte
        repartition[statut] += 1
        code = indicateur.element.project.code
        par_projet.setdefault(code, {"code": code, "atteint": 0, "en_cours": 0, "en_retard": 0})
        par_projet[code][statut] += 1

    couverture = list(
        menages.values("zone__parent__name")
        .annotate(menages=Count("id"))
        .order_by("-menages")[:10]
    )

    return {
        "role": "suivi_evaluation",
        "tuiles": {
            "indicateurs": indicateurs.count(),
            "menages": menages.count(),
            "individus": Person.objects.filter(household__in=menages).count(),
            "activites_validees": Activity.objects.filter(
                project__in=projets, status=Activity.Status.VALIDEE
            ).count(),
        },
        "repartition_indicateurs": repartition,
        "par_projet": sorted(par_projet.values(), key=lambda p: p["code"]),
        "sadd": _sadd(menages),
        "couverture_geographique": couverture,
        "qualite": {
            "doublons_en_attente": DuplicateCandidate.objects.filter(
                status=DuplicateCandidate.Status.A_ARBITRER
            ).count(),
            "menages_non_valides": menages.filter(
                validation_status=Household.ValidationStatus.A_VALIDER
            ).count(),
        },
    }


# ------------------------------------------------------------- financier
def tableau_financier(user):
    from funding.services import financements_accessibles

    financements = financements_accessibles(user).select_related("donor", "currency")
    aujourdhui = timezone.localdate()

    alertes = [
        {
            "convention": g.contract_number, "bailleur": str(g.donor),
            "consomme": g.taux_consommation, "temps_ecoule": g.taux_temps_ecoule,
            "ecart": g.ecart_rythme, "type": g.alerte_rythme,
        }
        for g in financements if g.alerte_rythme
    ]

    par_bailleur = {}
    for financement in financements:
        cle = str(financement.donor)
        entree = par_bailleur.setdefault(
            cle, {"bailleur": cle, "conventions": 0, "montant": Decimal("0"),
                  "depense": Decimal("0")}
        )
        entree["conventions"] += 1
        entree["montant"] += financement.amount
        entree["depense"] += financement.montant_depense

    return {
        "role": "charge_financier",
        "tuiles": {
            "conventions": financements.count(),
            "depenses_a_valider": Expense.objects.filter(
                budget_line__grant__in=financements, status=Expense.Status.SAISIE
            ).count(),
            "alertes_rythme": len(alertes),
            "echeances_30j": ReportDeadline.objects.filter(
                grant__in=financements,
                status__in=[ReportDeadline.Status.A_FAIRE, ReportDeadline.Status.EN_COURS],
                due_date__lte=aujourdhui + timedelta(days=30),
            ).count(),
        },
        "par_bailleur": [
            {**e, "montant": str(e["montant"]), "depense": str(e["depense"])}
            for e in sorted(par_bailleur.values(), key=lambda b: b["bailleur"])
        ],
        "alertes": alertes,
        "conventions": [
            {
                "id": g.id, "numero": g.contract_number, "bailleur": str(g.donor),
                "montant": str(g.amount), "devise": g.currency.code,
                "consomme": g.taux_consommation, "temps_ecoule": g.taux_temps_ecoule,
                "ecart": g.ecart_rythme, "fin_eligibilite": g.eligibility_end,
            }
            for g in financements
        ],
    }


# ------------------------------------------------------------- direction
def tableau_direction(user):
    projets = projets_accessibles(user)
    menages = _menages_du_perimetre(projets)
    financements = Grant.objects.filter(project_links__project__in=projets).distinct()

    indicateurs = Indicator.objects.filter(element__project__in=projets)
    en_retard = sum(1 for i in indicateurs if i.statut_atteinte == "en_retard")

    alertes = []
    for financement in financements.select_related("donor"):
        if financement.alerte_rythme:
            alertes.append({
                "type": financement.alerte_rythme,
                "objet": financement.contract_number,
                "detail": f"{financement.ecart_rythme:+} points d'ecart",
            })
    for echeance in ReportDeadline.objects.filter(
        grant__in=financements,
        status__in=[ReportDeadline.Status.A_FAIRE, ReportDeadline.Status.EN_COURS],
        due_date__lte=timezone.localdate() + timedelta(days=15),
    ).select_related("grant")[:5]:
        alertes.append({
            "type": "echeance_proche",
            "objet": echeance.grant.contract_number,
            "detail": f"{echeance.get_type_display()} dans {echeance.jours_restants} jours",
        })

    return {
        "role": "direction",
        "tuiles": {
            "projets_en_cours": projets.filter(status=Project.Status.EN_COURS).count(),
            "personnes_atteintes": Person.objects.filter(household__in=menages).count(),
            "menages": menages.count(),
            "conventions": financements.count(),
        },
        "projets_par_statut": list(
            projets.values("status").annotate(n=Count("id")).order_by("status")
        ),
        "financements": {
            "montant_total": str(
                financements.aggregate(t=Sum("amount"))["t"] or Decimal("0")
            ),
            "nb_bailleurs": financements.values("donor").distinct().count(),
        },
        "indicateurs_en_retard": en_retard,
        "sadd": _sadd(menages),
        "alertes": alertes[:10],
    }


# --------------------------------------------------------------- dispatch
TABLEAUX = {
    "agent_terrain": tableau_agent,
    "superviseur": tableau_superviseur,
    "chef_projet": tableau_projet,
    "coordinateur": tableau_projet,
    "suivi_evaluation": tableau_suivi_evaluation,
    "charge_financier": tableau_financier,
    "direction": tableau_direction,
    "bailleur": tableau_projet,
    "auditeur": tableau_direction,
}

# Ordre de priorite lorsqu'un utilisateur cumule plusieurs roles
PRIORITE = ["direction", "coordinateur", "charge_financier", "suivi_evaluation",
            "chef_projet", "superviseur", "agent_terrain", "bailleur", "auditeur"]


def tableau_par_defaut(user):
    """Choisit le tableau de bord le plus pertinent pour l'utilisateur."""
    if user.is_superuser:
        return tableau_direction(user)
    codes = set(user.roles.values_list("code", flat=True))
    for code in PRIORITE:
        if code in codes:
            return TABLEAUX[code](user)
    return {"role": None, "tuiles": {}, "message": "Aucun role attribue."}