from rest_framework.routers import DefaultRouter

from .views import ActivityViewSet

router = DefaultRouter()
router.register("activites", ActivityViewSet, basename="activite")

urlpatterns = router.urls