from django.urls import path

from .carto import ActivitesCartoView, CouvertureCartoView, SitesCartoView
from .exports import (
    ActivitesExportView,
    BeneficiairesExportView,
    IndicateursExportView,
    QuatreWExportView,
)
from .portail import (
    ChiffresPublicsView,
    OrganisationPubliqueView,
    ProjetsPublicsView,
    SecteursPublicsView,
)
from .views import TableauDeBordView, TableauProjetView

urlpatterns = [
    path("tableau-de-bord/", TableauDeBordView.as_view(), name="tableau-de-bord"),
    path("tableau-de-bord/projet/<int:pk>/", TableauProjetView.as_view(),
         name="tableau-de-bord-projet"),

    # cartographie
    path("carto/sites/", SitesCartoView.as_view(), name="carto-sites"),
    path("carto/activites/", ActivitesCartoView.as_view(), name="carto-activites"),
    path("carto/couverture/", CouvertureCartoView.as_view(), name="carto-couverture"),

    # exports
    path("exports/beneficiaires/", BeneficiairesExportView.as_view(), name="export-beneficiaires"),
    path("exports/activites/", ActivitesExportView.as_view(), name="export-activites"),
    path("exports/4w/", QuatreWExportView.as_view(), name="export-4w"),
    path("exports/indicateurs/", IndicateursExportView.as_view(), name="export-indicateurs"),


    # portail public — sans authentification
    path("portail/organisation/", OrganisationPubliqueView.as_view(), name="portail-organisation"),
    path("portail/chiffres/", ChiffresPublicsView.as_view(), name="portail-chiffres"),
    path("portail/projets/", ProjetsPublicsView.as_view(), name="portail-projets"),
    path("portail/secteurs/", SecteursPublicsView.as_view(), name="portail-secteurs"),
]