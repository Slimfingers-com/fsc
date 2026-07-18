class FSCError(Exception):
    """Basisklasse für fachliche FSC-Fehler."""


class EntityNotFoundError(FSCError):
    """Ein angefordertes Fachobjekt wurde nicht gefunden."""


class SourceNotFoundError(EntityNotFoundError):
    """Eine angeforderte Quelle wurde nicht gefunden."""


class DuplicateSourceError(FSCError):
    """Eine Quelle mit derselben eindeutigen Identität existiert bereits."""


class BusinessRuleViolationError(FSCError):
    """Eine fachliche Regel wurde verletzt."""
