from rest_framework.routers import DefaultRouter

from .views import NotificationPreferenceViewSet, NotificationViewSet

router = DefaultRouter()
router.register("notifications", NotificationViewSet, basename="notification")
router.register("preferences-notifications", NotificationPreferenceViewSet,
                basename="preference-notification")

urlpatterns = router.urls