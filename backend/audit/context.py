"""Contexte de la requete en cours, accessible depuis les signaux."""
import contextvars

_requete_courante = contextvars.ContextVar("requete_courante", default=None)


def definir_requete(request):
    return _requete_courante.set(request)


def reinitialiser(jeton):
    _requete_courante.reset(jeton)


def requete_courante():
    return _requete_courante.get()


def utilisateur_courant():
    request = _requete_courante.get()
    if request is None:
        return None
    utilisateur = getattr(request, "user", None)
    if utilisateur is not None and utilisateur.is_authenticated:
        return utilisateur
    return None