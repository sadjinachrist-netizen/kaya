from rest_framework.routers import DefaultRouter

from .views import DuplicateCandidateViewSet, HouseholdViewSet

router = DefaultRouter()
router.register("menages", HouseholdViewSet, basename="menage")
router.register("doublons", DuplicateCandidateViewSet, basename="doublon")

urlpatterns = router.urls