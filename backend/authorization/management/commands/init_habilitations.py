"""Charge les roles, les permissions et leurs attributions.

Traduction executable de la matrice du chapitre 9 du cahier d'analyse.
Commande idempotente : elle peut etre relancee autant de fois que voulu.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from authorization.models import Permission, Role, RolePermission

# Ordre des colonnes de la matrice : ADM DIR COO CDP SUP AGT M&E FIN BAI AUD
ROLES = [
    ("admin_systeme", "Administrateur systeme", True,
     "Gere les comptes, les roles, les referentiels et la configuration technique. "
     "N'accede a aucune donnee nominative de beneficiaire."),
    ("direction", "Direction", True,
     "Vision consolidee du portefeuille, des financements et de la performance. "
     "Approuve les projets et valide les rapports avant soumission au bailleur."),
    ("coordinateur", "Coordinateur de programmes", False,
     "Supervise un portefeuille de projets et arbitre entre eux."),
    ("chef_projet", "Chef de projet", False,
     "Pilote ses projets : equipe, budget, cadre logique, rapports bailleurs."),
    ("superviseur", "Superviseur terrain", False,
     "Controle et valide les saisies de son equipe, veille a la qualite des donnees."),
    ("agent_terrain", "Agent terrain", False,
     "Collecte les donnees sur le terrain, majoritairement hors connexion."),
    ("suivi_evaluation", "Charge de suivi-evaluation", False,
     "Definit et suit les indicateurs, analyse et produit les exports. "
     "Role transversal, independant des equipes projet."),
    ("charge_financier", "Charge financier", True,
     "Saisit et suit les financements, les budgets et les depenses."),
    ("bailleur", "Bailleur", False,
     "Consulte uniquement les projets qu'il finance. Lecture seule, "
     "sans acces aux donnees nominatives des beneficiaires."),
    ("auditeur", "Auditeur", False,
     "Consultation integrale en lecture seule, avec acces au journal d'audit."),
]

# (code, module, intitule, matrice)
#   P = permission complete    R = limitee a la portee    . = non accordee
PERMISSIONS = [
    # ---------------------------------------- Securite et administration
    ("utilisateur.creer", "securite", "Creer un compte utilisateur", "P........."),
    ("utilisateur.modifier", "securite", "Modifier un compte", "P........."),
    ("utilisateur.desactiver", "securite", "Desactiver un compte", "P........."),
    ("role.gerer", "securite", "Creer un role et lui affecter des permissions", "P........."),
    ("portee.affecter", "securite", "Affecter une portee a un utilisateur", "P........."),
    ("organisation.parametrer", "securite", "Parametrer l'identite de l'ONG", "P........."),
    ("referentiel.gerer", "securite", "Gerer zones, secteurs, devises, bailleurs", "P......P.."),
    ("audit.consulter", "securite", "Consulter le journal d'audit", "PP.......P"),
    # ------------------------------------------------------------ Projets
    ("projet.creer", "projets", "Creer un projet", "..PP......"),
    ("projet.modifier", "projets", "Modifier un projet", "..PR......"),
    ("projet.approuver", "projets", "Approuver un projet en instruction", ".PP......."),
    ("projet.suspendre", "projets", "Suspendre ou reprendre un projet", ".PPR......"),
    ("projet.cloturer", "projets", "Cloturer un projet", ".PPR......"),
    ("projet.consulter", "projets", "Consulter la fiche projet", ".PPRRRPPRP"),
    ("equipe.gerer", "projets", "Constituer et modifier l'equipe projet", "..PR......"),
    # --------------------------------------------- Financements et budget
    ("financement.creer", "financements", "Enregistrer une convention", ".......P.."),
    ("financement.modifier", "financements", "Modifier une convention", ".......P.."),
    ("financement.consulter", "financements", "Consulter les financements", ".PPR..PPRP"),
    ("budget.gerer", "financements", "Structurer les lignes budgetaires", ".......P.."),
    ("depense.saisir", "financements", "Saisir une depense", ".......P.."),
    ("depense.valider", "financements", "Valider une depense", ".......P.."),
    ("budget.consulter", "financements", "Consulter l'execution budgetaire", ".PPR..PPRP"),
    # ----------------------------------------------------- Beneficiaires
    ("beneficiaire.creer", "beneficiaires", "Enregistrer un menage", ".....P...."),
    ("beneficiaire.modifier", "beneficiaires", "Modifier un menage", "....PR...."),
    ("beneficiaire.valider", "beneficiaires", "Valider un menage enregistre", "....P....."),
    ("beneficiaire.consulter", "beneficiaires", "Consulter les menages", ".RRRRRR..R"),
    ("beneficiaire.voir_donnees_nominatives", "beneficiaires",
     "Acceder aux champs nominatifs", "...RRRR..."),
    ("beneficiaire.exporter", "beneficiaires", "Exporter les donnees beneficiaires", ".P.R..P..."),
    ("doublon.arbitrer", "beneficiaires", "Arbitrer un doublon candidat", "....P....."),
    # --------------------------------------------------- Activites terrain
    ("activite.creer", "activites", "Enregistrer une activite", ".....P...."),
    ("activite.modifier", "activites", "Modifier sa propre activite non validee", ".....R...."),
    ("activite.valider", "activites", "Valider ou rejeter une activite", "...RR....."),
    ("activite.consulter", "activites", "Consulter les activites", ".PPRRRP.RP"),
    ("collecte.hors_ligne", "activites", "Precharger et saisir hors connexion", "....PP...."),
    ("synchronisation.resoudre_conflit", "activites",
     "Trancher un conflit de synchronisation", "....P....."),
    # ----------------------------------------------------- Suivi-evaluation
    ("cadre_logique.gerer", "suivi", "Construire le cadre logique", "..PR......"),
    ("indicateur.definir", "suivi", "Definir un indicateur et ses desagregations", "......P..."),
    ("indicateur.relever", "suivi", "Saisir un releve periodique", "...R..P..."),
    ("indicateur.valider", "suivi", "Valider un releve", "......P..."),
    ("indicateur.consulter", "suivi", "Consulter les indicateurs", ".PPRRRPPRP"),
    ("indicateur.consolider", "suivi", "Consolider les indicateurs institutionnels", ".P....P..."),
    # --------------------------------------------------------- Restitution
    ("rapport.rediger", "restitution", "Rediger un rapport", "...R.RP..."),
    ("rapport.valider", "restitution", "Valider un rapport avant soumission", ".PP......."),
    ("rapport.soumettre_bailleur", "restitution", "Soumettre un rapport au bailleur", "...R......"),
    ("rapport.consulter", "restitution", "Consulter les rapports", ".PPRRRPPRP"),
    ("export.realiser", "restitution", "Realiser un export Excel ou 4W", ".PPR..PPRP"),
    ("portail.publier", "restitution", "Publier un contenu sur le portail public", "PP........"),
]

ETENDUES = {"P": RolePermission.Scope.GLOBAL, "R": RolePermission.Scope.PORTEE}


class Command(BaseCommand):
    help = "Charge les roles et permissions definis dans le cahier d'analyse."

    @transaction.atomic
    def handle(self, *args, **options):
        # Garde-fou : toute ligne de matrice doit avoir une case par role
        for code, _module, _label, matrice in PERMISSIONS:
            if len(matrice) != len(ROLES):
                raise ValueError(
                    f"Matrice incoherente pour '{code}' : "
                    f"{len(matrice)} cases pour {len(ROLES)} roles."
                )

        roles = {}
        for code, label, mfa, description in ROLES:
            role, _ = Role.objects.update_or_create(
                code=code,
                defaults={"label": label, "requires_mfa": mfa, "description": description},
            )
            roles[code] = role

        permissions = {}
        for code, module, label, _matrice in PERMISSIONS:
            perm, _ = Permission.objects.update_or_create(
                code=code, defaults={"module": module, "label": label}
            )
            permissions[code] = perm

        # La matrice du document fait autorite : on repart d'elle
        RolePermission.objects.all().delete()

        attributions = []
        for code, _module, _label, matrice in PERMISSIONS:
            for index, symbole in enumerate(matrice):
                if symbole == ".":
                    continue
                attributions.append(
                    RolePermission(
                        role=roles[ROLES[index][0]],
                        permission=permissions[code],
                        scope=ETENDUES[symbole],
                    )
                )
        RolePermission.objects.bulk_create(attributions)

        globales = sum(1 for a in attributions if a.scope == RolePermission.Scope.GLOBAL)
        self.stdout.write(self.style.SUCCESS(
            f"{len(roles)} roles, {len(permissions)} permissions, "
            f"{len(attributions)} attributions "
            f"({globales} completes, {len(attributions) - globales} limitees a la portee)."
        ))

        self.stdout.write("")
        for code, label, mfa, _d in ROLES:
            nb = roles[code].grants.count()
            marque = " [2FA obligatoire]" if mfa else ""
            self.stdout.write(f"  {label:<30} {nb:>3} permissions{marque}")