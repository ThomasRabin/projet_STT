from core.domain.auditeur import TestAuditeur, AuditErreur, AuditContext
from core.services.gestionnairePersistance import GestionnairePersistance

class TestReceptionneur:
    
    @staticmethod
    def recevoir_produit(data: dict) -> None:
        # 1. Validation des données d'entrée
        try:
            context = TestAuditeur.auditer_reception(AuditContext(
                produit=data.get("produit"),
                of=data.get("of"),
                of_object=data.get("of_object")
            ))
        except AuditErreur as e:
            print(f"Erreur d'audit lors de la réception : {e}")
            return
        
        # 2. Enregistrement du produit dans la base de données
        try:
            GestionnairePersistance.enregistrer_produit(context.produit)
            print("Produit enregistré avec succès.")
        except Exception as e:
            print(f"Erreur lors de l'enregistrement du produit : {e}")

