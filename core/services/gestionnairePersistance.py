from __future__ import annotations

from django.db import transaction
from django.utils.dateparse import parse_datetime

from core.domain.auditeur import RapportValide
from core.models import (
    ReferenceProduit,
    OF,
    Produit,
    AffectationProduitOF,
    Machine,
    InterfaceMachine,
    Operation,
    Test,
    LogTest,
    Defaut,
)


class GestionnairePersistance:
    """
    Écrit le rapport validé en base.
    """

    @transaction.atomic
    def persister(self, rapport: RapportValide) -> None:
        # 1) Référence PN
        reference_produit, _ = ReferenceProduit.objects.get_or_create(
            PN=rapport.pn,
            defaults={"description": None},
        )

        # 2) OF
        of_obj, _ = OF.objects.get_or_create(
            numeroOF=rapport.numero_of,
            defaults={
                "idReferenceProduit": reference_produit,
                "client": rapport.client,
                "quantite": rapport.quantite_of,
            },
        )

        # Si OF existe déjà, on peut mettre à jour client/quantite si tu veux :
        of_obj.client = rapport.client
        of_obj.idReferenceProduit = reference_produit
        of_obj.quantite = rapport.quantite_of
        of_obj.save()

        # 3) Produit
        produit_obj, _ = Produit.objects.get_or_create(
            SN=rapport.sn,
            defaults={
                "idReferenceProduit": reference_produit,
                "statutProduit": rapport.statut_produit,
            },
        )
        produit_obj.idReferenceProduit = reference_produit
        produit_obj.statutProduit = rapport.statut_produit
        produit_obj.save()

        # 4) Affectation Produit-OF (historique)
        # Ici on évite de recréer si la dernière affectation est déjà la même OF
        derniere_affectation = (
            AffectationProduitOF.objects.filter(idProduit=produit_obj)
            .order_by("-dateAffectation")
            .first()
        )
        if derniere_affectation is None or derniere_affectation.idOF_id != of_obj.id:
            AffectationProduitOF.objects.create(idProduit=produit_obj, idOF=of_obj)

        # 5) Machine
        machine_obj, _ = Machine.objects.get_or_create(
            codeMachine=rapport.code_machine,
            defaults={
                "nomMachine": rapport.code_machine,
                "typeMachine": rapport.type_machine,
                "anneeMachine": 2000,  # à adapter / rendre optionnel
                "dateDerniereMaintenanceMachine": "2025-01-01",  # idem
            },
        )
        machine_obj.typeMachine = rapport.type_machine
        machine_obj.save()

        # 6) Interfaces
        interfaces_objs = []
        for code_interface in rapport.codes_interfaces:
            interface_obj, _ = InterfaceMachine.objects.get_or_create(
                codeInterface=code_interface,
                defaults={
                    "nomInterface": code_interface,
                    "anneeInterface": 2000,
                },
            )
            interfaces_objs.append(interface_obj)

        # On remplace la liste des interfaces associées à cette machine
        machine_obj.interfaces.set(interfaces_objs)

        # 7) Operation
        operation_obj = Operation.objects.create(
            idOF=of_obj,
            idMachine=machine_obj,
            nomOperation=rapport.nom_operation,
            typeOperation=rapport.type_operation,
            dateFinOperation=parse_datetime(rapport.date_fin_operation_iso),
        )

        # 8) Test
        test_obj = Test.objects.create(
            idProduit=produit_obj,
            idOperation=operation_obj,
            face=rapport.face_test,
            etatTest=rapport.etat_test,
            resultatTest=rapport.resultat_test,
            FPY_flag=rapport.fpy_flag,
            dateFinTest=parse_datetime(rapport.date_fin_test_iso),
            versionLogiciel=rapport.version_logiciel,
            codeOperateur=rapport.code_operateur,
        )

        # 9) Logs
        for log in rapport.logs:
            LogTest.objects.create(
                idTest=test_obj,
                dateEtape=parse_datetime(log.get("dateEtape")) if log.get("dateEtape") else None,
                numeroEtape=log.get("numeroEtape"),
                nomEtape=log.get("nomEtape", ""),
                limPlus=log.get("limPlus"),
                limMoins=log.get("limMoins"),
                valeurMesuree=log.get("valeurMesuree"),
                unite=log.get("unite"),
                resultatEtape=bool(log.get("resultatEtape")),
                composant=log.get("composant"),
                refComposant=log.get("refComposant"),
                face=log.get("face"),
                imageTest=None,  # image pour l'AOI
            )

        # 10) Defaut (optionnel)
        if rapport.defaut:
            Defaut.objects.create(
                idTest=test_obj,
                numeroDefaut=rapport.defaut.get("numeroDefaut"),
                nomDefaut=rapport.defaut.get("nomDefaut", ""),
                dateDefaut=parse_datetime(rapport.defaut.get("dateDefaut")),
                dateRework=parse_datetime(rapport.defaut.get("dateRework"))
                if rapport.defaut.get("dateRework") else None,
                commentaireDefaut=rapport.defaut.get("commentaireDefaut"),
            )