"""
@file auditeur.py
@brief Validation métier des rapports de test entrants.

@details
Ce module contient la couche de validation métier appliquée après la
validation structurelle réalisée par les serializers DRF.

Le rôle de ce module est de :
- vérifier la cohérence entre le type de produit et la présence d'un panel ;
- vérifier la cohérence entre l'état du test, le résultat et le défaut ;
- vérifier la cohérence minimale des logs ;
- transformer le dictionnaire validé par DRF en objet métier RapportValide.

Format JSON attendu :
@code{.json}
{
  "idRapport": "...",
  "produit": {
    "type": "CARTE|PANEL",
    "sn": "...",
    "pn": "...",
    "statutProduit": "OK|A_ANALYSER|..."
  },
  "panel": null | {
    "nombreCartes": 30,
    "cartes": [...]
  },
  "of": {...},
  "operation": {...},
  "machine": {...},
  "test": {...},
  "defaut": null | {...},
  "logs": [...]
}
@endcode

La persistance finale est ensuite réalisée par GestionnairePersistance.
"""

from dataclasses import dataclass
from typing import Optional

from .exceptions import ErreurValidationMetier


@dataclass(frozen=True)
class RapportValide:
    """
    @brief Objet métier représentant un rapport validé.

    @details
    Cette classe contient uniquement des données déjà validées par :
    - les serializers DRF pour la structure et les types ;
    - AuditeurRapport pour les règles métier.

    Elle sert d'objet de transfert entre la couche domaine et la couche
    de persistance ORM.

    @var id_rapport
    Identifiant unique du rapport.

    @var pn
    Référence produit.

    @var sn
    Numéro de série du produit principal. Peut être nul pour certains cas
    de panels ou selon les données remontées par l'ETL.

    @var type_produit
    Type du produit principal : CARTE ou PANEL.

    @var statut_produit
    Statut métier du produit principal.

    @var statut_carte
    Ancien champ conservé pour compatibilité. Dans le format actuel, le
    statut des cartes est porté par panel.cartes.

    @var nombre_cartes_panel
    Nombre de cartes du panel si le produit est un panel.

    @var panel
    Données complètes du panel, ou None pour une carte unitaire.

    @var numero_of
    Numéro d'ordre de fabrication.

    @var client
    Nom du client.

    @var quantite_of
    Quantité de l'OF. Vaut 0 par défaut si absente du flux entrant.

    @var type_operation
    Type d'opération.

    @var numero_operation
    Numéro d'opération optionnel.

    @var nom_operation
    Nom de l'opération.

    @var date_fin_operation_iso
    Date de fin d'opération au format ISO, ou None.

    @var code_machine
    Code de la machine de test.

    @var type_machine
    Type de machine.

    @var code_interface
    Code de l'interface utilisée, ou None.

    @var face_test
    Face testée : TOP, BOTTOM ou None.

    @var etat_test
    Résultat booléen du test. True signifie test OK, False signifie test KO.

    @var resultat_test
    Résultat textuel du test.

    @var date_fin_test_iso
    Date de fin du test au format ISO.

    @var version_logiciel
    Version logicielle utilisée, ou None.

    @var code_operateur
    Code opérateur, ou None.

    @var logs
    Liste des logs de test.

    @var defaut
    Défaut associé au test, ou None si aucun défaut.
    """

    id_rapport: str

    pn: Optional[str]
    sn: Optional[str]
    type_produit: str
    statut_produit: str
    statut_carte: Optional[str]
    nombre_cartes_panel: Optional[int]
    panel: Optional[dict]

    numero_of: str
    client: Optional[str]
    quantite_of: int

    type_operation: str
    numero_operation: Optional[int]
    nom_operation: str
    date_fin_operation_iso: Optional[str]

    code_machine: str
    type_machine: str
    code_interface: Optional[str]

    face_test: Optional[str]
    etat_test: bool
    resultat_test: str
    date_fin_test_iso: str
    version_logiciel: Optional[str]
    code_operateur: Optional[int]

    logs: list[dict]
    defaut: Optional[dict]


class AuditeurRapport:
    """
    @brief Auditeur métier des rapports de test.

    @details
    Cette classe applique les règles métier qui ne relèvent pas uniquement
    du typage ou de la structure JSON.

    Les serializers DRF vérifient par exemple :
    - la présence des champs obligatoires ;
    - les types ;
    - les choix autorisés ;
    - les formats de dates ;
    - la structure générale.

    AuditeurRapport vérifie ensuite :
    - la cohérence CARTE / PANEL ;
    - la cohérence PASS / FAIL / défaut ;
    - la cohérence des positions dans les logs ;
    - la cohérence minimale des données avant persistance.

    @see RapportValide
    """

    def valider(self, rapport: dict) -> RapportValide:
        """
        @brief Valide les règles métier d'un rapport entrant.

        @details
        Le rapport reçu en paramètre doit déjà avoir été validé par
        RapportEntreeSerializer. Les dates sont donc normalement déjà des
        objets datetime Python.

        @param rapport
        Dictionnaire validé par le serializer DRF.

        @return RapportValide
        Objet métier prêt à être transmis à GestionnairePersistance.

        @throws ErreurValidationMetier
        Levée lorsqu'une règle métier n'est pas respectée.
        """

        produit = rapport["produit"]
        panel = rapport.get("panel")
        of_data = rapport["of"]
        operation = rapport["operation"]
        machine = rapport["machine"]
        test = rapport["test"]
        logs = rapport["logs"]
        defaut = rapport.get("defaut")

        type_produit = produit["type"]
        resultat_test_str = test["resultatTest"].strip().upper()
        etat_test = test["etatTest"]

        # ==========================================================
        # 1) Cohérence produit / panel
        # ==========================================================
        self._valider_coherence_produit_panel(
            type_produit=type_produit,
            panel=panel,
        )

        # ==========================================================
        # 2) Cohérence test / résultat / défaut
        # ==========================================================
        self._valider_coherence_test_defaut(
            etat_test=etat_test,
            resultat_test_str=resultat_test_str,
            defaut=defaut,
        )

        # ==========================================================
        # 3) Cohérence logs
        # ==========================================================
        self._valider_logs(
            logs=logs,
            type_produit=type_produit,
            panel=panel,
        )

        # ==========================================================
        # 4) Construction du rapport validé
        # ==========================================================
        return RapportValide(
            id_rapport=rapport["idRapport"],

            pn=produit.get("pn"),
            sn=produit.get("sn"),
            type_produit=type_produit,
            statut_produit=produit["statutProduit"],

            # Champ conservé pour compatibilité avec une ancienne structure.
            # Dans le format actuel, les statuts cartes sont dans :
            # rapport["panel"]["cartes"][x]["statutCarte"]
            statut_carte=None,

            nombre_cartes_panel=(panel or {}).get("nombreCartes"),
            panel=panel,

            numero_of=of_data["numeroOF"],
            client=of_data.get("client"),

            # Le serializer actuel ne contient pas quantite.
            # On met donc 0 par défaut pour rester compatible avec le modèle OF.
            quantite_of=of_data.get("quantite", 0),

            type_operation=operation["typeOperation"],
            numero_operation=operation.get("numeroOperation"),
            nom_operation=operation["nomOperation"],
            date_fin_operation_iso=(
                operation["dateFinOperation"].isoformat()
                if operation.get("dateFinOperation")
                else None
            ),

            code_machine=machine["codeMachine"],
            type_machine=machine["typeMachine"],
            code_interface=machine.get("interface"),

            face_test=test.get("face"),
            etat_test=etat_test,
            resultat_test=test["resultatTest"],
            date_fin_test_iso=test["dateFinTest"].isoformat(),
            version_logiciel=test.get("versionLogiciel"),
            code_operateur=test.get("codeOperateur"),

            logs=logs,
            defaut=defaut,
        )

    def _valider_coherence_produit_panel(
        self,
        *,
        type_produit: str,
        panel: Optional[dict],
    ) -> None:
        """
        @brief Valide la cohérence entre le type produit et le panel.

        @details
        Règles appliquées :
        - si le produit est une CARTE, le champ panel doit être null ;
        - si le produit est un PANEL, le champ panel doit être présent ;
        - pour un PANEL, le nombre de cartes déclaré doit correspondre au
          nombre d'éléments présents dans panel.cartes.

        @param type_produit
        Type du produit principal : CARTE ou PANEL.

        @param panel
        Objet panel reçu dans le JSON, ou None.

        @throws ErreurValidationMetier
        Si la cohérence produit/panel n'est pas respectée.
        """

        if type_produit == "CARTE":
            if panel is not None:
                raise ErreurValidationMetier(
                    "produit.type=CARTE mais panel doit être null"
                )

        elif type_produit == "PANEL":
            if panel is None:
                raise ErreurValidationMetier(
                    "produit.type=PANEL mais panel est absent"
                )

            nombre_cartes = panel.get("nombreCartes")
            cartes = panel.get("cartes", [])

            if nombre_cartes is None:
                raise ErreurValidationMetier(
                    "produit.type=PANEL mais panel.nombreCartes est absent"
                )

            if len(cartes) != nombre_cartes:
                raise ErreurValidationMetier(
                    "Le nombre de cartes dans panel.cartes ne correspond pas à panel.nombreCartes"
                )

        else:
            raise ErreurValidationMetier(
                "produit.type doit être CARTE ou PANEL"
            )

    def _valider_coherence_test_defaut(
        self,
        *,
        etat_test: bool,
        resultat_test_str: str,
        defaut: Optional[dict],
    ) -> None:
        """
        @brief Valide la cohérence entre le résultat du test et le défaut.

        @details
        Règles appliquées :
        - si etatTest=True, resultatTest doit contenir PASS ;
        - si etatTest=False, resultatTest ne doit pas contenir PASS ;
        - si etatTest=False, un défaut doit être présent ;
        - si etatTest=True, le défaut doit être null.

        @param etat_test
        Booléen indiquant si le test est réussi.

        @param resultat_test_str
        Résultat textuel du test, déjà normalisé en majuscules.

        @param defaut
        Objet défaut reçu dans le JSON, ou None.

        @throws ErreurValidationMetier
        Si la cohérence test/défaut n'est pas respectée.
        """

        if etat_test is True and "PASS" not in resultat_test_str:
            raise ErreurValidationMetier(
                "etatTest=True mais resultatTest n'indique pas PASS"
            )

        if etat_test is False and "PASS" in resultat_test_str:
            raise ErreurValidationMetier(
                "etatTest=False mais resultatTest contient PASS"
            )

        if etat_test is False:
            if defaut is None:
                raise ErreurValidationMetier(
                    "etatTest=False mais defaut est absent"
                )

            nom_defaut = defaut.get("nomDefaut")
            if nom_defaut is None or str(nom_defaut).strip() == "":
                raise ErreurValidationMetier(
                    "etatTest=False mais defaut.nomDefaut est absent"
                )

        if etat_test is True and defaut is not None:
            raise ErreurValidationMetier(
                "etatTest=True mais defaut doit être null"
            )

    def _valider_logs(
        self,
        *,
        logs: list[dict],
        type_produit: str,
        panel: Optional[dict],
    ) -> None:
        """
        @brief Valide la cohérence métier minimale des logs.

        @details
        Règles appliquées :
        - la liste des logs ne doit pas être vide ;
        - chaque log doit avoir une position ;
        - chaque position doit être supérieure ou égale à 1 ;
        - pour une CARTE, la position doit être 1 ;
        - pour un PANEL, la position ne doit pas dépasser nombreCartes.

        @param logs
        Liste des logs de test.

        @param type_produit
        Type du produit principal : CARTE ou PANEL.

        @param panel
        Objet panel reçu dans le JSON, ou None.

        @throws ErreurValidationMetier
        Si une règle de cohérence sur les logs n'est pas respectée.
        """

        if len(logs) == 0:
            raise ErreurValidationMetier("logs ne doit pas être vide")

        nombre_cartes = None
        if panel is not None:
            nombre_cartes = panel.get("nombreCartes")

        for index_log, log in enumerate(logs, start=1):
            position = log.get("position")

            if position is None:
                raise ErreurValidationMetier(
                    f"log #{index_log} : position manquante"
                )

            if position < 1:
                raise ErreurValidationMetier(
                    f"log #{index_log} : position doit être >= 1"
                )

            if type_produit == "CARTE" and position != 1:
                raise ErreurValidationMetier(
                    f"log #{index_log} : pour une CARTE, position doit être 1"
                )

            if type_produit == "PANEL":
                if nombre_cartes is not None and position > nombre_cartes:
                    raise ErreurValidationMetier(
                        f"log #{index_log} : position supérieure au nombre de cartes du panel"
                    )