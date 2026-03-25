"""
@file gestionnairePersistance.py
@brief Service de persistance : écrit un rapport validé en base via Django ORM.

@details
Ce module contient la classe @ref GestionnairePersistance qui transforme un
@ref RapportValide (objet déjà validé par la couche Domaine) en écritures SQL
réelles via l'ORM Django.

Responsabilités :
- Créer ou récupérer les entités nécessaires (référence PN, OF, produit, machine, interfaces).
- Mettre à jour certaines valeurs si l'entité existe déjà (ex : OF.client, OF.quantite).
- Gérer l'historisation Produit ↔ OF via la table @ref AffectationProduitOF.
- Créer ou mettre à jour la spécialisation Carte ou Panel selon le type produit.
- Insérer l'opération, le test, les logs et éventuellement le défaut.

Garanties :
- Toute l'opération est transactionnelle (@ref transaction.atomic) :
  soit tout passe, soit tout est annulé (rollback).

Limites / choix assumés :
- Certains champs "non applicables en v1" sont remplis avec des valeurs par défaut
  (anneeMachine, dateDerniereMaintenanceMachine, etc.).
"""

from __future__ import annotations

from django.db import IntegrityError, OperationalError, DatabaseError, transaction
from django.utils.dateparse import parse_datetime

from core.domain.auditeur import RapportValide
from core.domain.exceptions import (
    ErreurConflitRapport,
    ErreurTechniqueTemporaire,
)
from core.models import (
    ReferenceProduit,
    OF,
    AffectationProduitOF,
    Carte,
    Panel,
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
    Cette classe ne valide pas les données métier (c'est le rôle de l'Auditeur).
    Elle prend un @ref RapportValide et applique les opérations ORM nécessaires.
    """

    @transaction.atomic
    def persister(self, rapport: RapportValide) -> None:
        """
        @brief Persiste un rapport validé en base de données.

        @details
        Ordre logique des écritures :
        1) ReferenceProduit (PN)
        2) OF
        3) Produit spécialisé : Carte ou Panel
        4) Affectation Produit ↔ OF (historisation)
        5) Machine
        6) Interfaces + association ManyToMany
        7) Operation
        8) Test
        9) Logs
        10) Defaut (optionnel)

        @param rapport Objet @ref RapportValide produit par la validation métier.
        @return None

        @raises ErreurConflitRapport
            Si un conflit d'unicité ou un doublon est détecté.
        @raises ErreurTechniqueTemporaire
            Si la base est indisponible ou en erreur temporaire.
        """
        try:
            # ==========================================================
            # 1) Référence produit : créer ou récupérer par PN unique
            # ==========================================================
            reference_produit, _ = ReferenceProduit.objects.get_or_create(
                PN=rapport.pn,
                defaults={"description": None},
            )

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

            # Mise à jour si l'OF existe déjà
            of_obj.idReferenceProduit = reference_produit
            of_obj.client = rapport.client
            of_obj.quantite = rapport.quantite_of
            of_obj.save(
                update_fields=[
                    "idReferenceProduit",
                    "client",
                    "quantite",
                ]
            )

            # ==========================================================
            # 3) Produit spécialisé : Carte ou Panel
            #    IMPORTANT :
            #    On manipule directement le modèle enfant, pas Produit seul.
            # ==========================================================
            if rapport.type_produit == "CARTE":
                produit_obj, _ = Carte.objects.get_or_create(
                    SN=rapport.sn,
                    defaults={
                        "idReferenceProduit": reference_produit,
                        "statutProduit": rapport.statut_produit,
                        "statutCarte": rapport.statut_carte,
                    },
                )

                produit_obj.idReferenceProduit = reference_produit
                produit_obj.statutProduit = rapport.statut_produit
                produit_obj.statutCarte = rapport.statut_carte
                produit_obj.save(
                    update_fields=[
                        "idReferenceProduit",
                        "statutProduit",
                        "statutCarte",
                    ]
                )

            elif rapport.type_produit == "PANEL":
                produit_obj, _ = Panel.objects.get_or_create(
                    SN=rapport.sn,
                    defaults={
                        "idReferenceProduit": reference_produit,
                        "statutProduit": rapport.statut_produit,
                        "nombreCartes": rapport.nombre_cartes_panel,
                    },
                )

                produit_obj.idReferenceProduit = reference_produit
                produit_obj.statutProduit = rapport.statut_produit
                produit_obj.nombreCartes = rapport.nombre_cartes_panel
                produit_obj.save(
                    update_fields=[
                        "idReferenceProduit",
                        "statutProduit",
                        "nombreCartes",
                    ]
                )

            else:
                raise ErreurConflitRapport(
                    f"Type produit inconnu lors de la persistance : {rapport.type_produit}"
                )

            # ==========================================================
            # 4) Affectation Produit ↔ OF (historisation)
            #    Ne pas recréer une affectation si la dernière est identique
            # ==========================================================
            derniere_affectation = (
                AffectationProduitOF.objects.filter(idProduit=produit_obj)
                .order_by("-dateAffectation")
                .first()
            )

            if (
                derniere_affectation is None
                or derniere_affectation.idOF_id != of_obj.id
            ):
                AffectationProduitOF.objects.create(
                    idProduit=produit_obj,
                    idOF=of_obj,
                )

            # ==========================================================
            # 5) Machine : créer ou récupérer par codeMachine unique
            # ==========================================================
            machine_obj, _ = Machine.objects.get_or_create(
                codeMachine=rapport.code_machine,
                defaults={
                    "nomMachine": rapport.code_machine,
                    "typeMachine": rapport.type_machine,
                    "anneeMachine": 2000,  # TODO v2 : rendre optionnel ou fournir
                    "dateDerniereMaintenanceMachine": "2025-01-01",
                },
            )

            machine_obj.nomMachine = rapport.code_machine
            machine_obj.typeMachine = rapport.type_machine
            machine_obj.save(update_fields=["nomMachine", "typeMachine"])

            # ==========================================================
            # 6) Interface : créer/récupérer puis lier à la machine
            # ==========================================================

            interface_obj, _ = InterfaceMachine.objects.get_or_create(
                codeInterface=rapport.code_interface,
                defaults={
                    "nomInterface": rapport.code_interface,
                    "anneeInterface": 2000,  # TODO v2
                },
            )

            machine_obj.interfaces.add(interface_obj)

            # ==========================================================
            # 7) Operation : créer une opération
            # ==========================================================
            operation_obj = Operation.objects.create(
                idOF=of_obj,
                idMachine=machine_obj,
                numeroOperation=rapport.numero_operation,
                nomOperation=rapport.nom_operation,
                typeOperation=rapport.type_operation,
                dateFinOperation=(
                    parse_datetime(rapport.date_fin_operation_iso)
                    if rapport.date_fin_operation_iso
                    else None
                ),
            )

            tests_precedents_existent = PassageTest.objects.filter(idProduit=produit_obj).exists()

            fpy_calcule = (not tests_precedents_existent) and (rapport.etat_test is True)

            # ==========================================================
            # 8) Test : créer un passage de test
            # ==========================================================
            test_obj = PassageTest.objects.create(
                idProduit=produit_obj,
                idOperation=operation_obj,
                idInterfaceUtilisee=interface_obj,
                idRapport=rapport.id_rapport,
                face=rapport.face_test,
                etatTest=rapport.etat_test,
                resultatTest=rapport.resultat_test,
                codeOperateur=rapport.code_operateur,
                FPY_flag=fpy_calcule,
                dateFinTest=parse_datetime(rapport.date_fin_test_iso),
                versionLogiciel=rapport.version_logiciel,
            )

            # ==========================================================
            # 9) Logs : créer une ligne LogTest par entrée
            # ==========================================================
            for log in rapport.logs:
                LogTest.objects.create(
                    idTest=test_obj,
                    dateEtape=log.get("dateEtape"),
                    numeroEtape=log.get("numeroEtape"),
                    nomEtape=log.get("nomEtape", ""),
                    limPlus=log.get("limPlus"),
                    limMoins=log.get("limMoins"),
                    valeurMesuree=log.get("valeurMesuree"),
                    unite=log.get("unite"),
                    resultatEtape=log.get("resultatEtape"),
                    composant=log.get("composant"),
                    refComposant=log.get("refComposant"),
                    face=log.get("face"),
                    #imageTest=None,  abandonnée pour contraint memoire
                )

            # ==========================================================
            # 10) Défaut : optionnel, créé seulement si présent
            # ==========================================================
            if rapport.defaut:
                Defaut.objects.create(
                    idTest=test_obj,
                    numeroDefaut=rapport.defaut.get("numeroDefaut"),
                    nomDefaut=rapport.defaut.get("nomDefaut", ""),
                    dateDefaut=rapport.defaut.get("dateDefaut"),
                    dateRework=rapport.defaut.get("dateRework"),
                    commentaireDefaut=rapport.defaut.get("commentaireDefaut"),
                )

        except IntegrityError as exc:
            raise ErreurConflitRapport(
                f"Conflit de persistance SQL : {str(exc)}"
            ) from exc

        except OperationalError as exc:
            raise ErreurTechniqueTemporaire(
                "Base de données temporairement indisponible"
            ) from exc

        except DatabaseError as exc:
            raise ErreurTechniqueTemporaire(
                "Erreur technique lors de la persistance du rapport"
            ) from exc