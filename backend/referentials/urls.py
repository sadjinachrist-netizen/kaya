from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CurrencyViewSet,
    DonorViewSet,
    ExchangeRateViewSet,
    OrganisationView,
    SectorViewSet,
    VulnerabiliteViewSet,
    ZoneViewSet,
)

router = DefaultRouter()
router.register("zones", ZoneViewSet, basename="zone")
router.register("secteurs", SectorViewSet, basename="secteur")
router.register("bailleurs", DonorViewSet, basename="bailleur")
router.register("devises", CurrencyViewSet, basename="devise")
router.register("taux-change", ExchangeRateViewSet, basename="taux-change")
router.register("vulnerabilites", VulnerabiliteViewSet, basename="vulnerabilite")

urlpatterns = router.urls + [
    path("organisation", OrganisationView.as_view(), name="organisation"),
]