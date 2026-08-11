from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import ConnexionView, DeconnexionView, MoiView

urlpatterns = [
    path("login", ConnexionView.as_view(), name="connexion"),
    path("refresh", TokenRefreshView.as_view(), name="rafraichir"),
    path("logout", DeconnexionView.as_view(), name="deconnexion"),
    path("me", MoiView.as_view(), name="moi"),
]