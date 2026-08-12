from django.urls import path

from .views import TableauDeBordView, TableauProjetView

urlpatterns = [
    path("tableau-de-bord/", TableauDeBordView.as_view(), name="tableau-de-bord"),
    path("tableau-de-bord/projet/<int:pk>/", TableauProjetView.as_view(),
         name="tableau-de-bord-projet"),
]