from rest_framework.routers import DefaultRouter

from .views import IndicatorReadingViewSet, IndicatorViewSet, LogFrameElementViewSet

router = DefaultRouter()
router.register("cadre-logique", LogFrameElementViewSet, basename="cadre-logique")
router.register("indicateurs", IndicatorViewSet, basename="indicateur")
router.register("releves", IndicatorReadingViewSet, basename="releve")

urlpatterns = router.urls