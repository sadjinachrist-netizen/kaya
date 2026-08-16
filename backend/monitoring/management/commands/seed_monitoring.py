"""Cadre logique et indicateurs de demonstration.

A lancer apres seed_demo. Construit pour chaque projet actif un cadre
logique a quatre niveaux, des indicateurs calcules et manuels, puis des
releves trimestriels valides.
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from audit.context import audit_suspendu
from audit.services import journaliser
from monitoring.models import (
    Indicator,
    IndicatorDisaggregation,
    IndicatorReading,
    LogFrameElement,
)
from projects.models import Project

# (code, type, intitule, code du parent)
STRUCTURE = [
    ("OG1", "og", "Contribuer a l'amelioration durable des conditions de vie "
                  "des populations vulnerables de la zone d'intervention", None),
    ("OS1", "os", "Les menages vulnerables beneficient d'un appui direct adapte "
                  "a leurs besoins", "OG1"),
    ("OS2", "os", "Les capacites des communautes et des acteurs locaux sont renforcees", "OG1"),
    ("R1.1", "resultat", "Les menages vulnerables sont identifies et enregistres", "OS1"),
    ("R1.2", "resultat", "Les menages cibles recoivent l'appui prevu", "OS1"),
    ("R2.1", "resultat", "Les membres des communautes sont formes et sensibilises", "OS2"),
]

# (code, element, intitule, unite, mode, source, part de la cible projet)
INDICATEURS = [
    ("IND-1", "OS1", "Nombre de personnes atteintes par le projet",
     "personnes", "calcule", "individus_atteints", Decimal("1.00")),
    ("IND-2", "OS1", "Proportion de femmes parmi les personnes atteintes",
     "pourcentage", "manuel", "", None),
    ("IND-3", "R1.1", "Nombre de menages enregistres et valides",
     "menages", "calcule", "menages_atteints", Decimal("0.22")),
    ("IND-4", "R1.2", "Nombre d'activites de terrain realisees et validees",
     "nombre", "calcule", "activites_validees", Decimal("0.01")),
    ("IND-5", "R2.1", "Nombre de participants aux seances de formation "
                      "et de sensibilisation",
     "personnes", "calcule", "participants", Decimal("0.55")),
    ("IND-6", "R2.1", "Proportion de participants capables de citer trois "
                      "messages cles a l'issue de la seance",
     "pourcentage", "manuel", "", None),
]

DESAGREGATIONS = {
    "IND-1": ["sexe", "age", "zone"],
    "IND-3": ["zone", "vulnerabilite"],
    "IND-5": ["sexe", "age"],
}

COMMENTAIRES = [
    "Progression conforme aux previsions sur la periode.",
    "Retard lie a la saison des pluies, rattrapage prevu au trimestre suivant.",
    "Mobilisation communautaire superieure aux attentes.",
    "Difficultes d'acces a deux cantons, activites reportees.",
    "Resultats stables, qualite des seances jugee satisfaisante.",
]


class Command(BaseCommand):
    help = "Cree des cadres logiques et des indicateurs de demonstration."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        alea = random.Random(2026)

        charge_me = User.objects.filter(username="me.demo").first()
        if charge_me is None:
            self.stderr.write(self.style.ERROR(
                "Compte me.demo introuvable. Lancez d'abord : python manage.py seed_demo"
            ))
            return

        projets = list(Project.objects.filter(status="en_cours").order_by("code"))
        if not projets:
            self.stderr.write(self.style.ERROR("Aucun projet en cours."))
            return

        with audit_suspendu():
            if options["reset"]:
                IndicatorReading.objects.all().delete()
                IndicatorDisaggregation.objects.all().delete()
                Indicator.objects.all().delete()
                LogFrameElement.objects.all().delete()
                self.stdout.write(self.style.WARNING("Cadre logique supprime."))

            nb_indicateurs = 0
            nb_releves = 0
            aujourdhui = timezone.localdate()

            for projet in projets:
                # ---------------------------------------------- cadre logique
                elements = {}
                for position, (code, type_element, intitule, parent) in enumerate(STRUCTURE, 1):
                    elements[code] = LogFrameElement.objects.create(
                        project=projet,
                        type=type_element,
                        code=code,
                        title=intitule,
                        parent=elements.get(parent),
                        position=position,
                    )

                # ------------------------------------------------ indicateurs
                for code, code_element, intitule, unite, mode, source, part in INDICATEURS:
                    if part is not None:
                        cible = max(
                            Decimal(projet.target_beneficiaries) * part, Decimal("1")
                        ).quantize(Decimal("1"))
                    else:
                        cible = Decimal(alea.randint(55, 85))  # un pourcentage

                    if mode == "calcule":
                        definition = ("Valeur produite automatiquement a partir des "
                                      "donnees de la plateforme.")
                        verification = "Base de donnees Kaya"
                    else:
                        definition = ("Valeur issue d'une enquete aupres d'un "
                                      "echantillon representatif de beneficiaires.")
                        verification = "Rapport d'enquete trimestrielle"

                    indicateur = Indicator.objects.create(
                        element=elements[code_element],
                        code=f"{projet.code}-{code}",
                        title=intitule,
                        definition=definition,
                        unit=unite,
                        baseline=Decimal("0"),
                        target=cible,
                        frequency="trimestrielle",
                        verification_source=verification,
                        computation_mode=mode,
                        computation_source=source,
                        owner=charge_me,
                    )
                    nb_indicateurs += 1

                    for dimension in DESAGREGATIONS.get(code, []):
                        IndicatorDisaggregation.objects.create(
                            indicator=indicateur, dimension=dimension
                        )

                    # ---------------------------------------------- releves
                    # Trajectoire d'atteinte volontairement variee, pour que
                    # le tableau de bord montre du vert, de l'orange et du rouge.
                    trajectoire = alea.choices(
                        [Decimal("0.95"), Decimal("0.72"), Decimal("0.45")],
                        weights=[35, 40, 25],
                    )[0]

                    debut_periode = projet.start_date
                    trimestre = 0
                    releves = []
                    while debut_periode < min(aujourdhui, projet.end_date):
                        trimestre += 1
                        fin_periode = min(
                            debut_periode + timedelta(days=90),
                            projet.end_date,
                            aujourdhui,
                        )
                        if fin_periode <= debut_periode:
                            break

                        duree_projet = (projet.end_date - projet.start_date).days or 1
                        jours_ecoules = (fin_periode - projet.start_date).days
                        avancement = Decimal(str(
                            min(max(jours_ecoules / duree_projet, 0.0), 1.0)
                        ))
                        precision = Decimal("0.1") if unite == "pourcentage" else Decimal("1")
                        valeur = (cible * trajectoire * avancement).quantize(precision)
                        releves.append(IndicatorReading(
                            indicator=indicateur,
                            period_start=debut_periode,
                            period_end=fin_periode,
                            achieved_value=valeur,
                            comment=alea.choice(COMMENTAIRES),
                            status=IndicatorReading.Status.VALIDE,
                            entered_by=charge_me,
                            validated_by=charge_me,
                        ))
                        debut_periode = fin_periode + timedelta(days=1)

                    IndicatorReading.objects.bulk_create(releves)
                    nb_releves += len(releves)

        journaliser(
            "modification",
            object_type="Demonstration",
            object_label="Chargement du cadre logique",
            detail=f"{len(projets)} projets, {nb_indicateurs} indicateurs, {nb_releves} releves",
        )

        self.stdout.write(self.style.SUCCESS(
            f"\n{len(projets)} cadres logiques, {LogFrameElement.objects.count()} elements, "
            f"{nb_indicateurs} indicateurs, {nb_releves} releves valides.\n"
        ))

        repartition = {"atteint": 0, "en_cours": 0, "en_retard": 0}
        for indicateur in Indicator.objects.select_related("element__project"):
            repartition[indicateur.statut_atteinte] += 1
        self.stdout.write("Repartition des indicateurs :")
        self.stdout.write(f"   atteints  (>= 90 %)  : {repartition['atteint']}")
        self.stdout.write(f"   en cours  (60-89 %)  : {repartition['en_cours']}")
        self.stdout.write(f"   en retard (< 60 %)   : {repartition['en_retard']}\n")