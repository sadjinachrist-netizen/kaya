"""Modele utilisateur - paquetage P1 Securite et habilitations."""
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Gestionnaire d'utilisateurs base sur l'email comme identifiant."""

    use_in_migrations = True

    def _create_user(self, email, username, password, **extra_fields):
        if not email:
            raise ValueError(_("L'adresse email est obligatoire."))
        if not username:
            raise ValueError(_("Le nom d'utilisateur est obligatoire."))
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, username, password, **extra_fields)

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("mfa_enabled", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Un superutilisateur doit avoir is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Un superutilisateur doit avoir is_superuser=True."))
        return self._create_user(email, username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Utilisateur de la plateforme Kaya.

    L'identifiant de connexion est l'email. Le nom d'utilisateur reste
    unique et sert a l'affichage ainsi qu'aux comptes de demonstration.
    """

    username = models.CharField(
        _("nom d'utilisateur"),
        max_length=150,
        unique=True,
        validators=[UnicodeUsernameValidator()],
        help_text=_("150 caracteres maximum. Lettres, chiffres et @/./+/-/_ uniquement."),
    )
    email = models.EmailField(_("adresse email"), unique=True)
    first_name = models.CharField(_("prenom"), max_length=100, blank=True)
    last_name = models.CharField(_("nom"), max_length=100, blank=True)
    phone = models.CharField(_("telephone"), max_length=30, blank=True)

    # Un compte n'est jamais supprime, il est desactive (regle de gestion 8.1)
    is_active = models.BooleanField(_("actif"), default=True)
    is_staff = models.BooleanField(_("acces a l'administration"), default=False)

    # Second facteur : obligatoire pour Administrateur, Direction et Finance
    mfa_enabled = models.BooleanField(_("double facteur active"), default=False)

    # Verrouillage apres cinq echecs consecutifs (regle de gestion 8.1)
    failed_login_attempts = models.PositiveSmallIntegerField(
        _("echecs de connexion consecutifs"), default=0
    )
    locked_until = models.DateTimeField(_("verrouille jusqu'a"), null=True, blank=True)

    date_joined = models.DateTimeField(_("date d'inscription"), default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = _("utilisateur")
        verbose_name_plural = _("utilisateurs")
        ordering = ["username"]

    def __str__(self):
        return f"{self.username} <{self.email}>"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username

    @property
    def is_locked(self):
        return self.locked_until is not None and self.locked_until > timezone.now()


    def has_permission(self, code):
        """Verifie si l'utilisateur detient la permission demandee."""
        if self.is_superuser:
            return True
        return self.roles.filter(permissions__code=code).exists()

    @property
    def permission_codes(self):
        """Ensemble des codes de permission effectifs de l'utilisateur."""
        from authorization.models import Permission

        if self.is_superuser:
            return set(Permission.objects.values_list("code", flat=True))
        return set(
            Permission.objects.filter(roles__users=self)
            .values_list("code", flat=True)
            .distinct()
        )

    @property
    def mfa_required(self):
        """Le second facteur est impose des qu'un role l'exige."""
        return self.mfa_enabled or self.roles.filter(requires_mfa=True).exists()


    def permission_scope(self, code):
        """Renvoie l'etendue d'une permission : 'global', 'portee' ou None.

        La valeur la plus permissive l'emporte en cas de cumul de roles.
        """
        if self.is_superuser:
            return "global"
        from authorization.models import RolePermission

        etendues = set(
            RolePermission.objects.filter(
                role__users=self, permission__code=code
            ).values_list("scope", flat=True)
        )
        if "global" in etendues:
            return "global"
        if "portee" in etendues:
            return "portee"
        return None