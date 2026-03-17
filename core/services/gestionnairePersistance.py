"""
@file gestionnairePersistance.py
@brief Service de persistance : écrit un rapport validé en base via Django ORM.

@details
Ce module contient la classe @ref GestionnairePersistance qui transforme un
@ref RapportValide (objet "déjà validé" par la couche Domain) en écritures SQL
réelles via l'ORM Django.

Responsabilités :
- Créer ou récupérer les entités nécessaires (référence PN, OF, produit, machine, interfaces).
- Mettre à jour certaines valeurs si l'entité existe déjà (ex : OF.client, OF.quantite).
- Gérer l'historisation Produit ↔ OF via la table @ref AffectationProduitOF.
- Insérer l'opération, le test, les logs et éventuellement le défaut.

Garanties :
- Toute l'opération est transactionnelle (@ref transaction.atomic) :
  soit tout passe, soit tout est annulé (rollback).

Limites / choix assumés :
- Certains champs "non applicables en v1" sont remplis avec des valeurs par défaut
  (anneeMachine, dateDerniereMaintenanceMachine, etc.). À terme, il faudra soit :
  - les rendre optionnels en base (null=True/blank=True),
  - soit les fournir dans le JSON.
"""

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
    PassageTest,
    LogTest,
    Defaut,
)


class GestionnairePersistance:
    """
    @brief Service applicatif chargé d'écrire un rapport validé en base.

    @details
    Cette classe ne valide pas les données (c'est le rôle de l'Auditeur).
    Elle prend un @ref RapportValide et applique les opérations CRUD nécessaires.
    """

    @transaction.atomic
    def persister(self, rapport: RapportValide) -> None:
        """
        @brief Persiste un rapport validé en base de données.

        @details
        Ordre logique des écritures :
        1) ReferenceProduit (PN)
        2) OF
        3) Produit
        4) Affectation Produit ↔ OF (historisation)
        5) Machine
        6) Interfaces + association ManyToMany
        7) Operation
        8) Test
        9) Logs
        10) Defaut (optionnel)

        @param rapport Objet @ref RapportValide produit par la validation métier.
        @return None

        @note
        Toute exception levée ici annule la transaction (rollback automatique).
        """

        # ==========================================================
        # 1) Référence PN : créer ou récupérer par PN unique
        # ==========================================================
        reference_produit, _ = ReferenceProduit.objects.get_or_create(
            PN=rapport.pn,
            defaults={"description": None},
        )
        # "_" signifie : on ignore le booléen "created" renvoyé par get_or_create()

        # ==========================================================
        # 2) OF : créer ou récupérer par numeroOF unique
        # ==========================================================
        of_obj, _ = OF.objects.get_or_create(
            numeroOF=rapport.numero_of,
            defaults={
                "idReferenceProduit": reference_produit,
                "client": rapport.client,
                "quantite": rapport.quantite_of,
            },
        )

        # Mise à jour si l'OF existe déjà (on garde la BDD cohérente avec le flux)
        of_obj.client = rapport.client
        of_obj.idReferenceProduit = reference_produit
        of_obj.quantite = rapport.quantite_of
        of_obj.save()

        # ==========================================================
        # 3) Produit : créer ou récupérer par SN unique
        # ==========================================================
        produit_obj, _ = Produit.objects.get_or_create(
            SN=rapport.sn,
            defaults={
                "idReferenceProduit": reference_produit,
                "statutProduit": rapport.statut_produit,
            },
        )

        # Mise à jour si déjà existant
        produit_obj.idReferenceProduit = reference_produit
        produit_obj.statutProduit = rapport.statut_produit
        produit_obj.save()

        # ==========================================================
        # 4) Affectation Produit ↔ OF (historisation)
        #    But : ne pas recréer une affectation si la dernière est identique
        # ==========================================================
        derniere_affectation = (
            AffectationProduitOF.objects.filter(idProduit=produit_obj)
            .order_by("-dateAffectation")
            .first()
        )

        # On crée seulement si :
        # - pas d'affectation précédente
        # - ou changement d'OF par rapport à la dernière
        if derniere_affectation is None or derniere_affectation.idOF_id != of_obj.id:
            AffectationProduitOF.objects.create(idProduit=produit_obj, idOF=of_obj)

        # ==========================================================
        # 5) Machine : créer ou récupérer par codeMachine unique
        # ==========================================================
        machine_obj, _ = Machine.objects.get_or_create(
            codeMachine=rapport.code_machine,
            defaults={
                "nomMachine": rapport.code_machine,
                "typeMachine": rapport.type_machine,
                "anneeMachine": 2000,  # TODO : rendre optionnel ou fournir dans JSON
                "dateDerniereMaintenanceMachine": "2025-01-01",  # idem
            },
        )

        # Mise à jour du type machine (peut changer si corrigé dans les données source)
        machine_obj.typeMachine = rapport.type_machine
        machine_obj.save()

        # ==========================================================
        # 6) Interfaces : créer/récupérer puis lier à la machine (ManyToMany)
        # ==========================================================
        interfaces_objs = []
        for code_interface in rapport.codes_interfaces:
            interface_obj, _ = InterfaceMachine.objects.get_or_create(
                codeInterface=code_interface,
                defaults={
                    "nomInterface": code_interface,
                    "anneeInterface": 2000,  # TODO : idem (optionnel ou JSON)
                },
            )
            interfaces_objs.append(interface_obj)

        # Remplace toutes les associations existantes par celles du rapport
        machine_obj.interfaces.set(interfaces_objs)

        # ==========================================================
        # 7) Operation : créer un enregistrement d'opération
        # ==========================================================
        operation_obj = Operation.objects.create(
            idOF=of_obj,
            idMachine=machine_obj,
            nomOperation=rapport.nom_operation,
            typeOperation=rapport.type_operation,
            dateFinOperation=parse_datetime(rapport.date_fin_operation_iso)
            if rapport.date_fin_operation_iso else None,
        )

        # ==========================================================
        # 8) Test : créer un test lié au produit + opération
        # ==========================================================
        test_obj = PassageTest.objects.create(
            idProduit=produit_obj,
            idOperation=operation_obj,
            idRapport=rapport.id_rapport,  # important : unicité du rapport
            face=rapport.face_test,
            etatTest=rapport.etat_test,
            resultatTest=rapport.resultat_test,
            FPY_flag=rapport.fpy_flag,
            dateFinTest=parse_datetime(rapport.date_fin_test_iso),
            versionLogiciel=rapport.version_logiciel,
            codeOperateur=rapport.code_operateur,
        )

        # ==========================================================
        # 9) Logs : créer une ligne LogTest par entrée du JSON
        # ==========================================================
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
                imageTest=None,  # TODO : gérer l'image si fournie (AOI)
            )

        # ==========================================================
        # 10) Défaut : optionnel, créé seulement si présent
        # ==========================================================
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