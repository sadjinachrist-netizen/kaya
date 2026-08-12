"""API de synchronisation hors ligne."""
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.models import AuditLog
from audit.services import journaliser
from authorization.permissions import PermissionMetier

from .services import CREE, DEJA_TRAITE, ERREUR, construire_lot, traiter_element

LIMITE_ELEMENTS = 200


class LotView(APIView):
    """GET /api/sync/lot — donnees a precharger avant une mission."""

    permission_classes = [IsAuthenticated, PermissionMetier]
    permission_codes = {"default": "collecte.hors_ligne"}

    def get(self, request):
        lot = construire_lot(request.user)
        journaliser(
            AuditLog.Action.CONSULTATION,
            actor=request.user,
            object_type="SyncLot",
            detail=(
                f"Prechargement : {lot['compteurs']['projets']} projets, "
                f"{lot['compteurs']['menages']} menages"
            ),
            request=request,
        )
        return Response(lot)


class EnvoiView(APIView):
    """POST /api/sync/envoi — remontee des saisies effectuees hors ligne.

    Chaque element est traite independamment : une erreur sur l'un
    n'empeche pas l'enregistrement des autres. Le client se fie au
    statut renvoye pour vider sa file d'attente.
    """

    permission_classes = [IsAuthenticated, PermissionMetier]
    permission_codes = {"default": "collecte.hors_ligne"}

    def post(self, request):
        elements = request.data.get("elements")
        if not isinstance(elements, list):
            raise ValidationError({"elements": "Une liste d'elements est attendue."})
        if len(elements) > LIMITE_ELEMENTS:
            raise ValidationError({"elements": (
                f"Envoi limite a {LIMITE_ELEMENTS} elements par lot."
            )})

        resultats = [traiter_element(request.user, element) for element in elements]
        synthese = {
            "recus": len(resultats),
            "crees": sum(1 for r in resultats if r["statut"] == CREE),
            "deja_traites": sum(1 for r in resultats if r["statut"] == DEJA_TRAITE),
            "erreurs": sum(1 for r in resultats if r["statut"] == ERREUR),
        }

        journaliser(
            AuditLog.Action.CREATION,
            actor=request.user,
            object_type="SyncEnvoi",
            detail=(
                f"Synchronisation : {synthese['crees']} crees, "
                f"{synthese['deja_traites']} deja traites, "
                f"{synthese['erreurs']} en erreur"
            ),
            request=request,
        )

        code_http = (
            status.HTTP_207_MULTI_STATUS if synthese["erreurs"] else status.HTTP_200_OK
        )
        return Response({"synthese": synthese, "resultats": resultats}, status=code_http)