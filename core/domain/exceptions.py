class ErreurRapport(Exception):
    """Exception de base du domaine."""
    code = "RAPPORT_ERROR"


class ErreurValidationMetier(ErreurRapport):
    """Erreur métier non récupérable."""
    code = "VALIDATION_METIER"


class ErreurConflitRapport(ErreurRapport):
    """Conflit fonctionnel ou doublon."""
    code = "CONFLIT_RAPPORT"


class ErreurTechniqueTemporaire(ErreurRapport):
    """Erreur technique temporaire, potentiellement rejouable."""
    code = "ERREUR_TECHNIQUE_TEMPORAIRE"