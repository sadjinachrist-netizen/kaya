"""Points d'entree d'authentification."""
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from audit.models import AuditLog
from audit.services import journaliser

from .serializers import ConnexionSerializer, UserSerializer


class ConnexionView(TokenObtainPairView):
    """POST /api/auth/login — renvoie les jetons, l'identite et les droits."""

    serializer_class = ConnexionSerializer
    permission_classes = [AllowAny]


class MoiView(APIView):
    """GET /api/auth/me — identite et droits de l'utilisateur connecte."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class DeconnexionView(APIView):
    """POST /api/auth/logout — revoque le jeton de rafraichissement."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        jeton = request.data.get("refresh")
        if not jeton:
            return Response(
                {"detail": "Le jeton de rafraichissement est requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(jeton).blacklist()
        except Exception:
            return Response(
                {"detail": "Jeton invalide ou deja revoque."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        journaliser(
            AuditLog.Action.DECONNEXION,
            actor=request.user,
            object_type="User",
            object_id=request.user.pk,
            detail="Deconnexion",
            request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)