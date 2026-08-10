"""Contexte de la requete en cours, accessible depuis les signaux."""
import contextlib
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


    import contextlib

_audit_actif = contextvars.ContextVar("audit_actif", default=True)


def audit_actif():
    return _audit_actif.get()


@contextlib.contextmanager
def audit_suspendu():
    """Suspend la journalisation automatique pour les traitements en masse.

    A n'utiliser que pour les chargements de reference, en ecrivant a la place
    une entree de synthese explicite.
    """
    jeton = _audit_actif.set(False)
    try:
        yield
    finally:
        _audit_actif.reset(jeton)