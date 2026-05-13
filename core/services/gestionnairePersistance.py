"""
@file gestionnairePersistance.py
@brief Service de persistance ORM des rapports validés.

@details
Ce module transforme un RapportValide en écritures base de données.

Fonctionnalités :
- création / mise à jour de la référence produit
- création / mise à jour OF
- création du produit principal (carte ou panel)
- création éventuelle des cartes d'un panel
- création de la composition panel/cartes
- création machine / interface
- création opération / test / logs / défaut

Toute la persistance est réalisée dans une transaction atomique.
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
    CompositionPanel,
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
    """

    @transaction.atomic
    def persister(self, rapport: RapportValide) -> None:
        """
        @brief Persiste un rapport validé en base.

        @param rapport Rapport métier validé.
        @return None

        @raises ErreurConflitRapport
        @raises ErreurTechniqueTemporaire
        """
        try:
            # ==========================================================
            # 0) Détection doublon rapport
            # ==========================================================
            if PassageTest.objects.filter(idRapport=rapport.id_rapport).exists():
                raise ErreurConflitRapport(
                    f"Rapport déjà reçu : {rapport.id_rapport}"
                )

            # ==========================================================
            # 1) Référence produit
            # ==========================================================
            reference_produit = None
            if rapport.pn:
                reference_produit, _ = ReferenceProduit.objects.get_or_create(
                    PN=rapport.pn,
                    defaults={"description": None},
                )

            # ==========================================================
            # 2) OF
            # ==========================================================
            of_obj, _ = OF.objects.get_or_create(
                numeroOF=rapport.numero_of,
                defaults={
                    "idReferenceProduit": reference_produit,
                    "client": rapport.client,
                    "quantite": 0,
                },
            )

            of_obj.idReferenceProduit = reference_produit
            of_obj.client = rapport.client
            of_obj.save(update_fields=["idReferenceProduit", "client"])

            # ==========================================================
            # 3) Produit principal
            # ==========================================================
            if rapport.type_produit == "CARTE":
                produit_obj, _ = Carte.objects.get_or_create(
                    SN=rapport.sn,
                    defaults={
                        "idReferenceProduit": reference_produit,
                        "statutProduit": rapport.statut_produit,
                    },
                )

                produit_obj.idReferenceProduit = reference_produit
                produit_obj.statutProduit = rapport.statut_produit
                produit_obj.save(update_fields=["idReferenceProduit", "statutProduit"])

            elif rapport.type_produit == "PANEL":
                produit_obj, _ = Panel.objects.get_or_create(
                    SN=rapport.sn,
                    defaults={
                        "idReferenceProduit": reference_produit,
                        "statutProduit": rapport.statut_produit,
                        "nombreCartes": rapport.panel["nombreCartes"] if rapport.panel else 0,
                    },
                )

                produit_obj.idReferenceProduit = reference_produit
                produit_obj.statutProduit = rapport.statut_produit
                produit_obj.nombreCartes = rapport.panel["nombreCartes"] if rapport.panel else 0
                produit_obj.save(
                    update_fields=["idReferenceProduit", "statutProduit", "nombreCartes"]
                )

                # ======================================================
                # 3bis) Composition du panel
                # ======================================================
                CompositionPanel.objects.filter(idPanel=produit_obj).delete()

                if rapport.panel:
                    for carte_data in rapport.panel["cartes"]:
                        sn_carte = carte_data.get("snCarte")
                        statut_carte = carte_data["statutCarte"]
                        position = carte_data["position"]

                        carte_obj = None

                        if sn_carte:
                            carte_obj, _ = Carte.objects.get_or_create(
                                SN=sn_carte,
                                defaults={
                                    "idReferenceProduit": reference_produit,
                                    "statutProduit": statut_carte,
                                },
                            )
                            carte_obj.idReferenceProduit = reference_produit
                            carte_obj.statutProduit = statut_carte
                            carte_obj.save(
                                update_fields=["idReferenceProduit", "statutProduit"]
                            )

                        CompositionPanel.objects.create(
                            idPanel=produit_obj,
                            idCarte=carte_obj,
                            position=position,
                            statutCarte=statut_carte,
                        )

            else:
                raise ErreurConflitRapport(
                    f"Type produit inconnu lors de la persistance : {rapport.type_produit}"
                )

            # ==========================================================
            # 4) Affectation Produit ↔ OF
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
            # 5) Machine
            # ==========================================================
            machine_obj, _ = Machine.objects.get_or_create(
                codeMachine=rapport.code_machine,
                defaults={
                    "nomMachine": rapport.code_machine,
                    "typeMachine": rapport.type_machine,
                    "anneeMachine": 2000,
                    "dateDerniereMaintenanceMachine": "2025-01-01",
                },
            )

            machine_obj.nomMachine = rapport.code_machine
            machine_obj.typeMachine = rapport.type_machine
            machine_obj.save(update_fields=["nomMachine", "typeMachine"])

            # ==========================================================
            # 6) Interface machine
            # ==========================================================
            interface_obj = None
            if rapport.code_interface:
                interface_obj, _ = InterfaceMachine.objects.get_or_create(
                    codeInterface=rapport.code_interface,
                    defaults={
                        "nomInterface": rapport.code_interface,
                        "anneeInterface": 2000,
                    },
                )
                machine_obj.interfaces.add(interface_obj)

            # ==========================================================
            # 7) Opération
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

            # ==========================================================
            # 8) Calcul FPY
            # ==========================================================
            tests_precedents_existent = PassageTest.objects.filter(
                idProduit=produit_obj
            ).exists()

            fpy_calcule = (not tests_precedents_existent) and (rapport.etat_test is True)

            # ==========================================================
            # 9) Test
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
            # 10) Logs
            # ==========================================================
            for log in rapport.logs:
                LogTest.objects.create(
                    idTest=test_obj,
                    dateEtape=log.get("dateEtape"),
                    face=log.get("face"),
                    position=log.get("position", 1),
                    numeroEtape=log.get("numeroEtape"),
                    nomEtape=log.get("nomEtape", ""),
                    messageErreur=log.get("messageErreur"),
                    limPlus=log.get("limPlus"),
                    limMoins=log.get("limMoins"),
                    valeurMesuree=log.get("valeurMesuree"),
                    unite=log.get("unite"),
                    resultatEtape=log.get("resultatEtape"),
                    composant=log.get("composant"),
                    refComposant=log.get("refComposant"),
                )

            # ==========================================================
            # 11) Défaut
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
                f"Base de données temporairement indisponible : {str(exc)}"
            ) from exc

        except DatabaseError as exc:
            raise ErreurTechniqueTemporaire(
                "Erreur technique lors de la persistance du rapport"
            ) from exc