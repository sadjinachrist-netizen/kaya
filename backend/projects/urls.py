from rest_framework.routers import DefaultRouter

from .views import ProjectViewSet

router = DefaultRouter()
router.register("projets", ProjectViewSet, basename="projet")

urlpatterns = router.urls