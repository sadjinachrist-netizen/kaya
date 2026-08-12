"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.reverse import reverse


@api_view(["GET"])
@permission_classes([AllowAny])
def racine_api(request):
    """Point d'entree de l'API : liste les ressources disponibles."""
    return Response({
        "nom": "API Kaya",
        "version": "1.0",
        "description": "Plateforme de gestion et de suivi de projets humanitaires",
        "authentification": {
            "connexion": reverse("connexion", request=request),
            "rafraichir": reverse("rafraichir", request=request),
            "profil": reverse("moi", request=request),
        },
        "ressources": {
            "projets": request.build_absolute_uri("/api/projets/"),
            "menages": request.build_absolute_uri("/api/menages/"),
            "activites": request.build_absolute_uri("/api/activites/"),
            "doublons": request.build_absolute_uri("/api/doublons/"),
            "zones": request.build_absolute_uri("/api/zones/"),
            "secteurs": request.build_absolute_uri("/api/secteurs/"),
            "financements": request.build_absolute_uri("/api/financements/"),
            "depenses": request.build_absolute_uri("/api/depenses/"),
            "indicateurs": request.build_absolute_uri("/api/indicateurs/"),
            "cadre_logique": request.build_absolute_uri("/api/cadre-logique/"),
            "tableau_de_bord": request.build_absolute_uri("/api/tableau-de-bord/"),
        },
    })


urlpatterns = [
    path("", racine_api, name="racine-api"),
    path("admin/", admin.site.urls),
    path("api/", racine_api, name="racine-api-prefixe"),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("projects.urls")),
    path("api/", include("beneficiaries.urls")),
    path("api/", include("activities.urls")),
    path("api/", include("referentials.urls")),
    path("api/", include("funding.urls")),
    path("api/", include("monitoring.urls")),
    path("api/", include("dashboards.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)