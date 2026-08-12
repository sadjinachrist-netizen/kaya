"""Jeu de donnees financier de demonstration.

A lancer apres seed_demo : rattache des conventions de financement aux
projets existants, avec leurs lignes budgetaires, depenses, echeances
de rapportage et tranches de versement.
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
from funding.models import (
    BudgetLine,
    Expense,
    Grant,
    GrantProject,
    Installment,
    ReportDeadline,
)
from projects.models import Project
from referentials.models import Currency, Donor

BAILLEURS = [
    ("UNICEF", "Fonds des Nations Unies pour l'enfance", "onu", "International"),
    ("PAM", "Programme alimentaire mondial", "onu", "International"),
    ("ECHO", "Protection civile et operations humanitaires europeennes", "ue", "Union europeenne"),
    ("GIZ", "Cooperation allemande au developpement", "bilateral", "Allemagne"),
    ("AFD", "Agence francaise de developpement", "bilateral", "France"),
    ("FONDATION-BM", "Fondation Bougie et Miel", "fondation", "Suisse"),
]

# (rubrique, categorie, part du budget)
STRUCTURE_BUDGET = [
    ("PERS", "Personnel du projet", "personnel", Decimal("0.28")),
    ("ACTI", "Mise en oeuvre des activites", "activites", Decimal("0.42")),
    ("EQUI", "Equipements et fournitures", "equipement", Decimal("0.12")),
    ("TRAN", "Transport et logistique", "transport", Decimal("0.08")),
    ("FONC", "Fonctionnement du bureau", "fonctionnement", Decimal("0.04")),
    ("ADMI", "Frais administratifs", "administratif", Decimal("0.06")),
]

DEPENSES = [
    "Salaires de l'equipe terrain", "Perdiems des agents", "Location de vehicule",
    "Carburant", "Achat de kits", "Impression des supports de formation",
    "Location de salle", "Restauration des participants", "Fournitures de bureau",
    "Communication et connexion internet", "Honoraires de consultant",
    "Maintenance des equipements",
]


class Command(BaseCommand):
    help = "Cree des conventions de financement de demonstration."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        alea = random.Random(2026)

        finance = User.objects.filter(username="finance.demo").first()
        if finance is None:
            self.stderr.write(self.style.ERROR(
                "Compte finance.demo introuvable. Lancez d'abord : python manage.py seed_demo"
            ))
            return

        projets = list(Project.objects.exclude(status="archive").order_by("code"))
        if not projets:
            self.stderr.write(self.style.ERROR("Aucun projet. Lancez d'abord seed_demo."))
            return

        with audit_suspendu():
            if options["reset"]:
                Expense.objects.all().delete()
                BudgetLine.objects.all().delete()
                Installment.objects.all().delete()
                ReportDeadline.objects.all().delete()
                GrantProject.objects.all().delete()
                Grant.objects.all().delete()
                self.stdout.write(self.style.WARNING("Donnees financieres supprimees."))

            # ------------------------------------------------------ bailleurs
            bailleurs = []
            for sigle, nom, type_bailleur, pays in BAILLEURS:
                bailleur, _ = Donor.objects.update_or_create(
                    acronym=sigle,
                    defaults={"name": nom, "type": type_bailleur, "country": pays,
                              "contact_email": f"contact@{sigle.lower()}.org"},
                )
                bailleurs.append(bailleur)

            euro = Currency.objects.get(code="EUR")
            franc = Currency.objects.get(code="XOF")

            # --------------------------------------------------- financements
            financements, lignes, depenses, echeances, versements = [], [], [], [], []
            aujourdhui = timezone.localdate()

            for index, projet in enumerate(projets[:9], start=1):
                bailleur = bailleurs[index % len(bailleurs)]
                devise = euro if index % 3 else franc
                montant = (
                    Decimal(alea.randrange(80, 460)) * 1000
                    if devise == euro
                    else Decimal(alea.randrange(40, 260)) * 1000000
                )
                debut = projet.start_date
                fin = projet.end_date

                financement = Grant.objects.create(
                    contract_number=f"{bailleur.acronym}-{debut.year}-{index:03d}",
                    title=f"Financement — {projet.title}",
                    donor=bailleur,
                    amount=montant,
                    currency=devise,
                    signature_date=debut - timedelta(days=alea.randint(15, 60)),
                    eligibility_start=debut,
                    eligibility_end=fin,
                    status=Grant.Status.SIGNE,
                )
                financements.append(financement)

                GrantProject.objects.create(
                    grant=financement, project=projet, share_percent=Decimal("100.00")
                )

                # ------------------------------------------ lignes budgetaires
                lignes_du_financement = []
                for code_rubrique, libelle, categorie, part in STRUCTURE_BUDGET:
                    ligne = BudgetLine.objects.create(
                        grant=financement,
                        code=f"{code_rubrique}",
                        label=libelle,
                        category=categorie,
                        budgeted_amount=(montant * part).quantize(Decimal("0.01")),
                    )
                    lignes_du_financement.append(ligne)
                    lignes.append(ligne)

                # ------------------------------------------------- depenses
                # Rythme volontairement varie : sous-consommation, normal, depassement
                profil = alea.choices(
                    ["sous", "normal", "depassement"], weights=[45, 45, 10]
                )[0]
                cible = {"sous": 0.35, "normal": 0.75, "depassement": 1.08}[profil]

                for ligne in lignes_du_financement:
                    reste = ligne.budgeted_amount * Decimal(str(cible))
                    nb = alea.randint(3, 8)
                    for _ in range(nb):
                        if reste <= 0:
                            break
                        part_depense = (reste / nb * Decimal(str(alea.uniform(0.6, 1.4)))
                                        ).quantize(Decimal("0.01"))
                        if part_depense <= 0:
                            continue
                        jours = alea.randint(0, max((min(aujourdhui, fin) - debut).days, 1))
                        depenses.append(Expense(
                            budget_line=ligne,
                            project=projet,
                            label=alea.choice(DEPENSES),
                            amount=part_depense,
                            currency=devise,
                            expense_date=debut + timedelta(days=jours),
                            status=alea.choices(
                                [Expense.Status.VALIDEE, Expense.Status.SAISIE],
                                weights=[85, 15],
                            )[0],
                            entered_by=finance,
                        ))
                        reste -= part_depense

                # --------------------------------------- echeances de rapport
                for numero, (type_rapport, decalage) in enumerate([
                    (ReportDeadline.Type.NARRATIF, 90),
                    (ReportDeadline.Type.FINANCIER, 180),
                    (ReportDeadline.Type.NARRATIF, 270),
                    (ReportDeadline.Type.FINAL, (fin - debut).days),
                ]):
                    echeance = debut + timedelta(days=decalage)
                    if echeance > fin:
                        echeance = fin
                    passee = echeance < aujourdhui
                    echeances.append(ReportDeadline(
                        grant=financement,
                        type=type_rapport,
                        due_date=echeance,
                        status=(ReportDeadline.Status.ACCEPTE if passee
                                else ReportDeadline.Status.A_FAIRE),
                        submitted_at=(timezone.now() - timedelta(days=10)) if passee else None,
                    ))

                # -------------------------------------------------- versements
                nb_tranches = alea.choice([2, 3])
                for tranche in range(nb_tranches):
                    date_prevue = debut + timedelta(days=tranche * 180)
                    recu = date_prevue < aujourdhui
                    versements.append(Installment(
                        grant=financement,
                        amount=(montant / nb_tranches).quantize(Decimal("0.01")),
                        expected_date=date_prevue,
                        received_date=date_prevue + timedelta(days=alea.randint(2, 25)) if recu else None,
                        status=Installment.Status.RECU if recu else Installment.Status.ATTENDU,
                    ))

            Expense.objects.bulk_create(depenses, batch_size=400)
            ReportDeadline.objects.bulk_create(echeances, batch_size=200)
            Installment.objects.bulk_create(versements, batch_size=200)

            # Une echeance imminente, pour rendre l'alerte visible en demo
            imminente = ReportDeadline.objects.filter(
                status=ReportDeadline.Status.A_FAIRE
            ).order_by("due_date").first()
            if imminente:
                imminente.due_date = aujourdhui + timedelta(days=5)
                imminente.save(update_fields=["due_date"])

        journaliser(
            "modification",
            object_type="Demonstration",
            object_label="Chargement du jeu financier",
            detail=f"{len(financements)} financements, {len(depenses)} depenses",
        )

        self.stdout.write(self.style.SUCCESS(
            f"\n{len(bailleurs)} bailleurs, {len(financements)} conventions, "
            f"{len(lignes)} lignes budgetaires, {Expense.objects.count()} depenses, "
            f"{ReportDeadline.objects.count()} echeances, "
            f"{Installment.objects.count()} tranches.\n"
        ))
        self.stdout.write("Rythme de consommation par convention :")
        for financement in Grant.objects.select_related("donor", "currency").order_by("contract_number"):
            alerte = financement.alerte_rythme or "—"
            self.stdout.write(
                f"   {financement.contract_number:<22} "
                f"consomme {financement.taux_consommation:>5} %  "
                f"temps {financement.taux_temps_ecoule:>5} %  "
                f"ecart {financement.ecart_rythme:>+6} pts  {alerte}"
            )