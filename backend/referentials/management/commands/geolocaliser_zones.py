"""Renseigne les coordonnees des prefectures du Togo.

Coordonnees approchees des chefs-lieux, suffisantes pour une carte a
l'echelle nationale. Elles ne remplacent pas un referentiel officiel.
La commande est idempotente : elle ne touche que les zones sans coordonnees,
sauf si --forcer est passe.
"""
from django.core.management.base import BaseCommand

from referentials.models import Zone

# prefecture -> (latitude, longitude) du chef-lieu
PREFECTURES = {
    # --- Maritime
    "Golfe": (6.172, 1.231),            # Lome
    "Agoe-Nyive": (6.201, 1.201),       # Agoe
    "Zio": (6.426, 1.213),              # Tsevie
    "Ave": (6.421, 0.923),              # Keve
    "Yoto": (6.585, 1.501),             # Tabligbo
    "Vo": (6.334, 1.531),               # Vogan
    "Lacs": (6.228, 1.591),             # Aneho
    "Bas-Mono": (6.443, 1.634),         # Afanyangan
    # --- Plateaux
    "Ogou": (7.533, 1.133),             # Atakpame
    "Kloto": (6.900, 0.629),            # Kpalime
    "Agou": (6.871, 0.752),             # Agou-Gadzepe
    "Amou": (7.468, 0.902),             # Amlame
    "Anie": (7.750, 1.183),             # Anie
    "Haho": (6.951, 1.169),             # Notse
    "Kpele": (6.982, 0.731),            # Kpele-Adeta
    "Wawa": (7.584, 0.601),             # Badou
    "Est-Mono": (7.601, 1.421),         # Elavagnon
    "Moyen-Mono": (7.021, 1.531),       # Tohoun
    "Danyi": (7.048, 0.631),            # Danyi-Apeyeme   (moins sur)
    "Akebou": (7.752, 0.752),           # Kougnohou       (moins sur)
    # --- Centrale
    "Tchaoudjo": (8.983, 1.133),        # Sokode
    "Sotouboua": (8.562, 0.984),        # Sotouboua
    "Blitta": (8.318, 0.981),           # Blitta
    "Tchamba": (9.031, 1.421),          # Tchamba
    "Mo": (8.871, 0.723),               # Djarkpanga      (moins sur)
    # --- Kara
    "Kozah": (9.551, 1.186),            # Kara
    "Assoli": (9.351, 1.268),           # Bafilo
    "Bassar": (9.251, 0.783),           # Bassar
    "Binah": (9.752, 1.281),            # Pagouda
    "Doufelgou": (9.768, 1.102),        # Niamtougou
    "Keran": (9.958, 1.048),            # Kande
    "Dankpen": (9.621, 0.581),          # Guerin-Kouka
    # --- Savanes
    "Tone": (10.862, 0.207),            # Dapaong
    "Cinkasse": (11.128, 0.032),        # Cinkasse
    "Oti": (10.361, 0.471),             # Sansanne-Mango
    "Tandjouare": (10.721, 0.201),      # Tandjoare
    "Kpendjal": (10.851, 0.831),        # Mandouri
    "Kpendjal-Ouest": (10.951, 0.552),  # Naki-Est        (moins sur)
    "Oti-Sud": (10.201, 0.602),         # Gando           (moins sur)
}


class Command(BaseCommand):
    help = "Renseigne les coordonnees des prefectures du Togo."

    def add_arguments(self, parseur):
        parseur.add_argument(
            "--forcer",
            action="store_true",
            help="Ecrase les coordonnees deja presentes.",
        )

    def handle(self, *args, **options):
        mises_a_jour = 0
        introuvables = []

        for nom, (latitude, longitude) in PREFECTURES.items():
            zone = Zone.objects.filter(level=Zone.Level.PREFECTURE, name=nom).first()
            if zone is None:
                introuvables.append(nom)
                continue
            if zone.latitude is not None and not options["forcer"]:
                continue
            zone.latitude = latitude
            zone.longitude = longitude
            zone.save(update_fields=["latitude", "longitude"])
            mises_a_jour += 1

        restantes = Zone.objects.filter(
            level=Zone.Level.PREFECTURE, latitude__isnull=True
        ).values_list("name", flat=True)

        self.stdout.write(self.style.SUCCESS(f"{mises_a_jour} prefectures geolocalisees."))
        if introuvables:
            self.stdout.write(
                self.style.WARNING(f"Absentes de la base : {', '.join(introuvables)}")
            )
        if restantes:
            self.stdout.write(
                self.style.WARNING(f"Toujours sans coordonnees : {', '.join(restantes)}")
            )