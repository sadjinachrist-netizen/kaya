"""API des tableaux de bord."""
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authorization.scopes import projets_accessibles

from .services import TABLEAUX, tableau_par_defaut, tableau_projet


class TableauDeBordView(APIView):
    """GET /api/tableau-de-bord/ — tableau adapte au role de l'utilisateur.

    Un parametre `role` permet de demander explicitement un autre tableau,
    a condition que l'utilisateur detienne ce role.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = request.query_params.get("role")
        if not role:
            return Response(tableau_par_defaut(request.user))

        if role not in TABLEAUX:
            raise NotFound(f"Tableau de bord inconnu : {role}")
        detenus = set(request.user.roles.values_list("code", flat=True))
        if role not in detenus and not request.user.is_superuser:
            raise PermissionDenied("Vous ne detenez pas ce role.")
        return Response(TABLEAUX[role](request.user))


class TableauProjetView(APIView):
    """GET /api/tableau-de-bord/projet/<id>/ — tableau d'un projet precis."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        projet = projets_accessibles(request.user).filter(pk=pk).first()
        if projet is None:
            raise NotFound("Projet introuvable ou hors de votre portee.")
        donnees = tableau_projet(request.user, projet=projet)
        donnees["projet"] = {
            "id": projet.id, "code": projet.code, "titre": projet.title,
            "statut": projet.status, "debut": projet.start_date, "fin": projet.end_date,
            "avancement": projet.calculer_avancement(),
        }
        return Response(donnees)