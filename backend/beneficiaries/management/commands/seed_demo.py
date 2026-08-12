"""Jeu de donnees de demonstration realiste pour Kaya.

Cree les comptes de demonstration, un portefeuille de projets et une
population de menages avec leurs membres, leurs consentements et
quelques doublons volontaires.

Toutes les personnes sont fictives.
"""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from audit.context import audit_suspendu
from audit.services import journaliser
from authorization.models import Role, UserScope
from beneficiaries.models import (
    Consent,
    DuplicateCandidate,
    Household,
    HouseholdProject,
    Person,
    Vulnerability,
)
from projects.models import InterventionSite, Project, TeamMember
from referentials.models import Sector, Zone

MOT_DE_PASSE = "Demo2026Kaya"

COMPTES = [
    ("direction.demo", "direction", "Ama", "Kponton"),
    ("chef.demo", "chef_projet", "Afi", "Amouzou"),
    ("superviseur.demo", "superviseur", "Komla", "Attiogbe"),
    ("agent.demo", "agent_terrain", "Kossi", "Amegan"),
    ("me.demo", "suivi_evaluation", "Sena", "Dogbe"),
    ("finance.demo", "charge_financier", "Edem", "Lawson"),
    ("bailleur.demo", "bailleur", "Claire", "Fontaine"),
]

VULNERABILITES = [
    ("femme-cheffe-menage", "Femme cheffe de menage", 3),
    ("handicap", "Personne en situation de handicap", 3),
    ("enfant-non-accompagne", "Enfant non accompagne ou separe", 4),
    ("personne-agee-isolee", "Personne agee isolee", 3),
    ("femme-enceinte", "Femme enceinte ou allaitante", 2),
    ("malade-chronique", "Malade chronique", 2),
]

PRENOMS_M = ["Kossi", "Kofi", "Yao", "Komla", "Kodjo", "Mawuli", "Elom", "Edem",
             "Selom", "Komi", "Akouete", "Sena", "Dela", "Fiifi"]
PRENOMS_F = ["Afi", "Ama", "Adjo", "Essi", "Abra", "Akouvi", "Dede", "Yawa",
             "Enyonam", "Akpene", "Mawuena", "Sitsofe", "Delali", "Edoh"]
NOMS = ["Amegan", "Agbeko", "Adjovi", "Kponton", "Amouzou", "Attiogbe", "Dogbe",
        "Lawson", "Mensah", "Nyavor", "Sossou", "Akakpo", "Bodjona", "Folly",
        "Djeri", "Aziaba", "Tettey", "Gbedemah", "Ahiavi", "Koudjo"]

LIENS = ["Epouse", "Epoux", "Fils", "Fille", "Mere", "Pere", "Neveu", "Niece", "Petit-fils"]

# (code, intitule, secteur, region, statut, cible)
PROJETS = [
    ("PRJ-2026-001", "Nutrition communautaire dans la Kara", "nutrition", "kara", "en_cours", 2400),
    ("PRJ-2026-002", "Sante maternelle et infantile - Savanes", "sante", "savanes", "en_cours", 3100),
    ("PRJ-2026-003", "Acces a l'eau potable - Plateaux", "wash", "plateaux", "en_cours", 5200),
    ("PRJ-2026-004", "Scolarisation des filles - Centrale", "education", "centrale", "en_cours", 1800),
    ("PRJ-2026-005", "Securite alimentaire - Oti", "securite-alimentaire", "savanes", "en_cours", 4300),
    ("PRJ-2026-006", "Assainissement peri-urbain - Maritime", "wash", "maritime", "en_cours", 6000),
    ("PRJ-2026-007", "Appui aux moyens de subsistance - Kara", "moyens-subsistance", "kara", "en_cours", 1200),
    ("PRJ-2026-008", "Protection de l'enfance - Lome", "protection", "maritime", "en_cours", 900),
    ("PRJ-2026-009", "Cantines scolaires - Plateaux", "education", "plateaux", "approuve", 2700),
    ("PRJ-2026-010", "Prevention du paludisme - Centrale", "sante", "centrale", "approuve", 3500),
    ("PRJ-2025-011", "Rehabilitation de forages - Savanes", "wash", "savanes", "cloture", 4100),
    ("PRJ-2025-012", "Nutrition infantile - Maritime", "nutrition", "maritime", "cloture", 2200),
]


class Command(BaseCommand):
    help = "Cree un jeu de donnees de demonstration realiste."

    def add_arguments(self, parser):
        parser.add_argument("--menages", type=int, default=120,
                            help="Nombre de menages a generer.")
        parser.add_argument("--reset", action="store_true",
                            help="Supprime les donnees de demonstration existantes.")

    @transaction.atomic
    def handle(self, *args, **options):
        alea = random.Random(2026)  # reproductible
        nb_menages = options["menages"]

        with audit_suspendu():
            if options["reset"]:
                DuplicateCandidate.objects.all().delete()
                HouseholdProject.objects.all().delete()
                Person.objects.all().delete()
                Consent.objects.all().delete()
                Household.objects.all().delete()
                TeamMember.objects.all().delete()
                InterventionSite.objects.all().delete()
                UserScope.objects.all().delete()
                Project.objects.all().delete()
                User.objects.filter(username__endswith=".demo").delete()
                self.stdout.write(self.style.WARNING("Donnees de demonstration supprimees."))

            # ---------------------------------------------------- vulnerabilites
            for code, libelle, poids in VULNERABILITES:
                Vulnerability.objects.update_or_create(
                    code=code, defaults={"label": libelle, "weight": poids}
                )
            vulnerabilites = list(Vulnerability.objects.all())

            # ---------------------------------------------------------- comptes
            comptes = {}
            for nom_utilisateur, code_role, prenom, nom in COMPTES:
                utilisateur, cree = User.objects.get_or_create(
                    username=nom_utilisateur,
                    defaults={
                        "email": f"{nom_utilisateur}@kaya.tg",
                        "first_name": prenom,
                        "last_name": nom,
                    },
                )
                if cree:
                    utilisateur.set_password(MOT_DE_PASSE)
                    utilisateur.save()
                role = Role.objects.get(code=code_role)
                role.users.add(utilisateur)
                comptes[code_role] = utilisateur

            chef = comptes["chef_projet"]
            agent = comptes["agent_terrain"]
            superviseur = comptes["superviseur"]

            # La direction et le M&E voient tout
            for cle in ("direction", "suivi_evaluation", "charge_financier"):
                UserScope.objects.get_or_create(
                    user=comptes[cle], scope_type=UserScope.Type.GLOBAL
                )

            # ---------------------------------------------------------- projets
            projets = []
            for code, intitule, secteur, region, statut, cible in PROJETS:
                zone_region = Zone.objects.get(code=region)
                prefectures = list(zone_region.children.all())
                debut = date(2025 if code.startswith("PRJ-2025") else 2026,
                             alea.randint(1, 6), 1)
                projet, _ = Project.objects.update_or_create(
                    code=code,
                    defaults={
                        "title": intitule,
                        "description": f"Projet {intitule.lower()} mis en oeuvre par SDT.",
                        "start_date": debut,
                        "end_date": debut + timedelta(days=alea.randint(360, 720)),
                        "status": statut,
                        "target_beneficiaries": cible,
                        "manager": chef,
                    },
                )
                projet.sectors.set([Sector.objects.get(code=secteur)])
                for prefecture in alea.sample(prefectures, min(2, len(prefectures))):
                    InterventionSite.objects.get_or_create(
                        project=projet,
                        zone=prefecture,
                        defaults={"target_population": alea.randint(4000, 25000)},
                    )
                projets.append(projet)

            # L'agent et le superviseur sont affectes aux six premiers projets
            for projet in projets[:6]:
                TeamMember.objects.get_or_create(
                    project=projet, user=agent,
                    project_role=TeamMember.ProjectRole.AGENT,
                    defaults={"start_date": projet.start_date},
                )
                TeamMember.objects.get_or_create(
                    project=projet, user=superviseur,
                    project_role=TeamMember.ProjectRole.SUPERVISEUR,
                    defaults={"start_date": projet.start_date},
                )

            # --------------------------------------------------------- menages
            projets_actifs = [p for p in projets if p.status == "en_cours"]
            annee = timezone.now().year
            depart = Household.objects.filter(code__startswith=f"BEN-{annee}-").count()

            menages, membres, consentements, liens = [], [], [], []
            noms_utilises = []

            for index in range(nb_menages):
                projet = alea.choice(projets_actifs)
                zone = alea.choice(list(projet.sites.all())).zone
                chef_femme = alea.random() < 0.32
                prenom = alea.choice(PRENOMS_F if chef_femme else PRENOMS_M)
                nom_chef = f"{prenom} {alea.choice(NOMS)}".upper()
                taille = alea.choices([1, 2, 3, 4, 5, 6, 7, 8],
                                      weights=[4, 8, 14, 20, 20, 16, 11, 7])[0]

                menage = Household(
                    code=f"BEN-{annee}-{depart + index + 1:06d}",
                    head_name=nom_chef,
                    size=taille,
                    zone=zone,
                    latitude=Decimal(str(round(alea.uniform(6.1, 11.0), 6))),
                    longitude=Decimal(str(round(alea.uniform(0.0, 1.8), 6))),
                    gps_accuracy=alea.randint(4, 35),
                    residence_status=alea.choices(
                        ["resident", "deplace", "retourne"], weights=[86, 10, 4]
                    )[0],
                    registered_by=agent,
                    registered_at=timezone.now() - timedelta(days=alea.randint(0, 120)),
                    validation_status=alea.choices(
                        ["valide", "a_valider"], weights=[78, 22]
                    )[0],
                )
                menages.append(menage)
                noms_utilises.append((nom_chef, zone))

            Household.objects.bulk_create(menages)
            menages = list(Household.objects.filter(
                code__in=[m.code for m in menages]
            ).select_related("zone"))

            for menage in menages:
                projet = alea.choice(projets_actifs)
                liens.append(HouseholdProject(household=menage, project=projet))
                consentements.append(Consent(
                    household=menage,
                    granted=True,
                    collection_mode=alea.choices(
                        ["oral", "ecrit", "empreinte"], weights=[58, 30, 12]
                    )[0],
                    collected_at=menage.registered_at,
                ))
                # chef de menage
                prenom_chef, nom_famille = menage.head_name.split(" ", 1)
                membres.append(Person(
                    household=menage, first_name=prenom_chef.title(),
                    last_name=nom_famille.title(),
                    sex="F" if prenom_chef.title() in PRENOMS_F else "M",
                    birth_date=date(alea.randint(1960, 2000), alea.randint(1, 12), alea.randint(1, 28)),
                    is_head=True, relation_to_head="Chef de menage",
                ))
                for _ in range(menage.size - 1):
                    sexe = alea.choice(["M", "F"])
                    naissance = date(alea.randint(1955, 2024), alea.randint(1, 12), alea.randint(1, 28))
                    age = timezone.localdate().year - naissance.year
                    membres.append(Person(
                        household=menage,
                        first_name=alea.choice(PRENOMS_F if sexe == "F" else PRENOMS_M),
                        last_name=nom_famille.title(),
                        sex=sexe,
                        birth_date=naissance,
                        relation_to_head=alea.choice(LIENS),
                        is_enrolled=(6 <= age <= 17 and alea.random() < 0.72),
                        has_disability=alea.random() < 0.05,
                    ))

            Person.objects.bulk_create(membres, batch_size=500)
            Consent.objects.bulk_create(consentements, batch_size=500)
            HouseholdProject.objects.bulk_create(liens, ignore_conflicts=True, batch_size=500)

            for menage in menages:
                if alea.random() < 0.28:
                    menage.vulnerabilities.set(
                        alea.sample(vulnerabilites, alea.randint(1, 2))
                    )

            # ------------------------------------------- doublons volontaires
            doublons = []
            for menage in alea.sample(menages, min(6, len(menages))):
                prenom, nom = menage.head_name.split(" ", 1)
                variante = f"{prenom[:-1]} {nom}" if len(prenom) > 4 else f"{prenom} {nom[:-1]}"
                jumeau = Household.objects.create(
                    code=f"BEN-{annee}-{depart + len(menages) + len(doublons) + 1:06d}",
                    head_name=variante,
                    size=menage.size,
                    zone=menage.zone,
                    registered_by=agent,
                    registered_at=menage.registered_at + timedelta(days=alea.randint(1, 20)),
                )
                Consent.objects.create(household=jumeau, granted=True, collection_mode="oral")
                Person.objects.create(
                    household=jumeau, first_name=prenom.title(), last_name=nom.title(),
                    sex="F" if prenom.title() in PRENOMS_F else "M",
                    birth_date=date(1985, 5, 12), is_head=True,
                    relation_to_head="Chef de menage",
                )
                doublons.append(DuplicateCandidate(
                    household_a=menage, household_b=jumeau,
                    score=Decimal(str(round(alea.uniform(0.86, 0.97), 3))),
                ))
            DuplicateCandidate.objects.bulk_create(doublons, ignore_conflicts=True)

        journaliser(
            "modification",
            object_type="Demonstration",
            object_label="Chargement du jeu de demonstration",
            detail=f"{len(projets)} projets, {len(menages)} menages, {len(membres)} individus",
        )

        total_personnes = Person.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"\n{len(COMPTES)} comptes, {len(projets)} projets, "
            f"{Household.objects.count()} menages, {total_personnes} individus, "
            f"{DuplicateCandidate.objects.count()} doublons a arbitrer.\n"
        ))
        self.stdout.write("Comptes de demonstration (mot de passe commun) :")
        for nom_utilisateur, code_role, _p, _n in COMPTES:
            self.stdout.write(f"   {nom_utilisateur + '@kaya.tg':<28} {code_role}")
        self.stdout.write(f"\n   Mot de passe : {MOT_DE_PASSE}\n")