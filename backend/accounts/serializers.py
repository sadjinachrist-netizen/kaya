"""Serialiseurs d'authentification."""
from django.conf import settings
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from audit.models import AuditLog
from audit.services import journaliser

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Identite et droits effectifs de l'utilisateur connecte."""

    full_name = serializers.CharField(read_only=True)
    roles = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    mfa_required = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "full_name", "phone", "roles", "permissions", "mfa_required",
            "is_staff", "is_superuser", "last_login",
        ]
        read_only_fields = fields

    def get_roles(self, obj):
        return list(obj.roles.values("code", "label"))

    def get_permissions(self, obj):
        """Codes de permission avec leur etendue."""
        if obj.is_superuser:
            from authorization.models import Permission

            return {code: "global" for code in Permission.objects.values_list("code", flat=True)}

        from authorization.models import RolePermission

        etendues = {}
        for code, scope in RolePermission.objects.filter(role__users=obj).values_list(
            "permission__code", "scope"
        ):
            # l'etendue la plus large l'emporte en cas de cumul de roles
            if etendues.get(code) != "global":
                etendues[code] = scope
        return etendues


class ConnexionSerializer(TokenObtainPairSerializer):
    """Connexion avec comptage des echecs et verrouillage temporaire."""

    def validate(self, attrs):
        request = self.context.get("request")
        email = attrs.get(self.username_field, "")
        utilisateur = User.objects.filter(email__iexact=email).first()

        if utilisateur and utilisateur.is_locked:
            journaliser(
                AuditLog.Action.ACCES_REFUSE,
                actor=utilisateur,
                object_type="User",
                object_id=utilisateur.pk,
                detail="Tentative sur un compte verrouille",
                request=request,
            )
            raise AuthenticationFailed(
                "Compte temporairement verrouille. Reessayez dans quelques minutes."
            )

        try:
            donnees = super().validate(attrs)
        except AuthenticationFailed:
            if utilisateur is not None:
                utilisateur.failed_login_attempts += 1
                champs = ["failed_login_attempts"]
                if utilisateur.failed_login_attempts >= settings.MAX_TENTATIVES_CONNEXION:
                    utilisateur.locked_until = timezone.now() + settings.DUREE_VERROUILLAGE
                    champs.append("locked_until")
                utilisateur.save(update_fields=champs)
            journaliser(
                AuditLog.Action.ACCES_REFUSE,
                actor=utilisateur,
                object_type="User",
                object_id=utilisateur.pk if utilisateur else "",
                detail=f"Echec de connexion pour '{email}'",
                request=request,
            )
            # Message volontairement generique : ne jamais reveler
            # si c'est l'identifiant ou le mot de passe qui est faux
            raise AuthenticationFailed("Identifiants incorrects.")

        if utilisateur.failed_login_attempts or utilisateur.locked_until:
            utilisateur.failed_login_attempts = 0
            utilisateur.locked_until = None
            utilisateur.save(update_fields=["failed_login_attempts", "locked_until"])

        journaliser(
            AuditLog.Action.CONNEXION,
            actor=utilisateur,
            object_type="User",
            object_id=utilisateur.pk,
            detail="Connexion reussie",
            request=request,
        )

        donnees["user"] = UserSerializer(utilisateur).data
        return donnees