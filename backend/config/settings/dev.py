"""Configuration de developpement local."""
from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Le front Next.js tournera sur le port 3000
CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]

# Les emails s'affichent dans la console, aucun envoi reel
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"