from dataclasses import dataclass
from typing import Optional

from .exceptions import ErreurValidationMetier


@dataclass(frozen=True)
class RapportValide:
    id_rapport: str

    pn: str
    sn: str
    type_produit: str
    statut_produit: str
    statut_carte: Optional[str]
    nombre_cartes_panel: Optional[int]

    numero_of: str
    client: str
    quantite_of: int

    type_operation: str
    numero_operation: Optional[int]
    nom_operation: str
    date_fin_operation_iso: Optional[str]

    code_machine: str
    type_machine: str
    code_interface: str

    face_test: Optional[str]
    etat_test: bool
    resultat_test: str
    date_fin_test_iso: str
    version_logiciel: Optional[str]
    code_operateur: Optional[int]

    logs: list[dict]
    defaut: Optional[dict]


class AuditeurRapport:
    def valider(self, rapport: dict) -> RapportValide:
        produit = rapport["produit"]
        of_data = rapport["of"]
        operation = rapport["operation"]
        machine = rapport["machine"]
        test = rapport["test"]
        logs = rapport["logs"]
        defaut = rapport.get("defaut")

        resultat_test_str = test["resultatTest"].strip().upper()
        etat_test = test["etatTest"]

        # ==========================================================
        # 1) Cohérence produit
        # ==========================================================
        if produit["type"] == "CARTE":
            if produit.get("carte") is None:
                raise ErreurValidationMetier(
                    "produit.type=CARTE mais produit.carte est absent"
                )
            if produit.get("panel") is not None:
                raise ErreurValidationMetier(
                    "produit.type=CARTE mais produit.panel doit être null"
                )

        elif produit["type"] == "PANEL":
            if produit.get("panel") is None:
                raise ErreurValidationMetier(
                    "produit.type=PANEL mais produit.panel est absent"
                )
            if produit.get("carte") is not None:
                raise ErreurValidationMetier(
                    "produit.type=PANEL mais produit.carte doit être null"
                )
        else:
            raise ErreurValidationMetier(
                "produit.type doit être CARTE ou PANEL"
            )

        # ==========================================================
        # 2) Cohérence test PASS / FAIL / défaut
        # ==========================================================
        if etat_test is True and "PASS" not in resultat_test_str:
            raise ErreurValidationMetier(
                "etatTest=True mais resultatTest n'indique pas PASS"
            )

        if etat_test is False and "PASS" in resultat_test_str:
            raise ErreurValidationMetier(
                "etatTest=False mais resultatTest contient PASS"
            )

        if etat_test is False and defaut is None:
            raise ErreurValidationMetier(
                "etatTest=False mais defaut est absent"
            )

        # ==========================================================
        # 3) Cohérence logs
        # ==========================================================
        if len(logs) == 0:
            raise ErreurValidationMetier("logs ne doit pas être vide")

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

            if produit["type"] == "CARTE" and position != 1:
                raise ErreurValidationMetier(
                    f"log #{index_log} : pour une CARTE, position doit être 1"
                )

        # ==========================================================
        # 4) Construction du rapport validé
        # ==========================================================
        return RapportValide(
            id_rapport=rapport["idRapport"],

            pn=produit["pn"],
            sn=produit["sn"],
            type_produit=produit["type"],
            statut_produit=produit["statutProduit"],
            statut_carte=(produit.get("carte") or {}).get("statutCarte"),
            nombre_cartes_panel=(produit.get("panel") or {}).get("nombreCartes"),

            numero_of=of_data["numeroOF"],
            client=of_data["client"],
            quantite_of=of_data["quantite"],

            type_operation=operation["typeOperation"],
            numero_operation=operation.get("numeroOperation"),
            nom_operation=operation["nomOperation"],
            date_fin_operation_iso=(
                operation["dateFinOperation"].isoformat()
                if operation.get("dateFinOperation") else None
            ),

            code_machine=machine["codeMachine"],
            type_machine=machine["typeMachine"],
            code_interface=machine["interface"],

            face_test=test.get("face"),
            etat_test=test["etatTest"],
            resultat_test=test["resultatTest"],
            date_fin_test_iso=test["dateFinTest"].isoformat(),
            version_logiciel=test.get("versionLogiciel"),
            code_operateur=test.get("codeOperateur"),

            logs=logs,
            defaut=defaut,
        )