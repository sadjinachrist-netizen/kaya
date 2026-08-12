from django.urls import path

from .views import EnvoiView, LotView

urlpatterns = [
    path("sync/lot", LotView.as_view(), name="sync-lot"),
    path("sync/envoi", EnvoiView.as_view(), name="sync-envoi"),
]