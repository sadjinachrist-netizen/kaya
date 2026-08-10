"""Charge les referentiels de base : organisation, devises, secteurs, geographie.

Commande idempotente : relancable sans creer de doublon.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from audit.context import audit_suspendu
from audit.services import journaliser
from referentials.models import Currency, Organization, Sector, Zone

DEVISES = [
    ("XOF", "Franc CFA (BCEAO)", "F CFA", True),
    ("EUR", "Euro", "\u20ac", False),
    ("USD", "Dollar des Etats-Unis", "$", False),
]

SECTEURS = [
    ("education", "Education"),
    ("sante", "Sante"),
    ("nutrition", "Nutrition"),
    ("wash", "Eau, hygiene et assainissement"),
    ("securite-alimentaire", "Securite alimentaire"),
    ("protection", "Protection"),
    ("moyens-subsistance", "Moyens de subsistance"),
    ("abris", "Abris et biens non alimentaires"),
]

# (nom de la region, chef-lieu, latitude, longitude, prefectures)
# Coordonnees du chef-lieu, approximatives : elles servent a centrer la carte.
GEOGRAPHIE = [
    ("Maritime", "Tsevie", 6.426, 1.213, [
        "Golfe", "Agoe-Nyive", "Ave", "Bas-Mono", "Lacs", "Vo", "Yoto", "Zio",
    ]),
    ("Plateaux", "Atakpame", 7.533, 1.133, [
        "Agou", "Akebou", "Amou", "Anie", "Danyi", "Est-Mono", "Haho",
        "Kloto", "Kpele", "Moyen-Mono", "Ogou", "Wawa",
    ]),
    ("Centrale", "Sokode", 8.983, 1.133, [
        "Blitta", "Mo", "Sotouboua", "Tchamba", "Tchaoudjo",
    ]),
    ("Kara", "Kara", 9.551, 1.186, [
        "Assoli", "Bassar", "Binah", "Dankpen", "Doufelgou", "Keran", "Kozah",
    ]),
    ("Savanes", "Dapaong", 10.862, 0.207, [
        "Cinkasse", "Kpendjal", "Kpendjal-Ouest", "Oti", "Oti-Sud",
        "Tandjouare", "Tone",
    ]),
]


def slug(valeur):
    return valeur.lower().replace(" ", "-").replace("'", "")


class Command(BaseCommand):
    help = "Charge les referentiels de base et le decoupage administratif du Togo."

    @transaction.atomic
    def handle(self, *args, **options):
        with audit_suspendu():
            organisation = Organization.get_solo()

            for code, nom, symbole, base in DEVISES:
                Currency.objects.update_or_create(
                    code=code,
                    defaults={"name": nom, "symbol": symbole, "is_base": base},
                )

            for code, libelle in SECTEURS:
                Sector.objects.update_or_create(
                    code=code, defaults={"label": libelle, "parent": None}
                )

            nb_regions = nb_prefectures = 0
            for nom_region, _chef_lieu, lat, lon, prefectures in GEOGRAPHIE:
                region, _ = Zone.objects.update_or_create(
                    code=slug(nom_region),
                    defaults={
                        "name": nom_region,
                        "level": Zone.Level.REGION,
                        "parent": None,
                        "latitude": lat,
                        "longitude": lon,
                    },
                )
                nb_regions += 1
                for nom_prefecture in prefectures:
                    Zone.objects.update_or_create(
                        code=slug(nom_prefecture),
                        defaults={
                            "name": nom_prefecture,
                            "level": Zone.Level.PREFECTURE,
                            "parent": region,
                        },
                    )
                    nb_prefectures += 1

        journaliser(
            "modification",
            object_type="Referentiels",
            object_label="Chargement des referentiels de base",
            detail=(
                f"{len(DEVISES)} devises, {len(SECTEURS)} secteurs, "
                f"{nb_regions} regions, {nb_prefectures} prefectures"
            ),
        )

        self.stdout.write(self.style.SUCCESS(
            f"Organisation : {organisation}\n"
            f"{len(DEVISES)} devises, {len(SECTEURS)} secteurs, "
            f"{nb_regions} regions, {nb_prefectures} prefectures."
        ))
        for nom_region, chef_lieu, _lat, _lon, prefectures in GEOGRAPHIE:
            self.stdout.write(f"  {nom_region:<12} ({chef_lieu:<10}) {len(prefectures):>2} prefectures")