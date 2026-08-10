"""Rend la requete courante accessible aux signaux d'audit."""
from .context import definir_requete, reinitialiser


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        jeton = definir_requete(request)
        try:
            return self.get_response(request)
        finally:
            reinitialiser(jeton)