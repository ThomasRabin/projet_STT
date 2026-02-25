from dataclasses import dataclass
from django.utils import timezone
from core.models import Produit, OF, AffectationProduitOF

class AuditErreur(Exception):
    pass

@dataclass
class AuditContext:
    produit: Produit
    of: OF | None
    of_object: OF | None

class TestAuditeur:
    
    @staticmethod
    def audit(payload: dict) -> AuditContext:
        for key in ("sn", "etat_test", "resultat_test", "fpy_flag"):
            if key not in payload:
                raise AuditErreur(f"Clé manquante dans le payload : {key}")
