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
    codes_interfaces: list[str]
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
        resultat_test_str = rapport["test"]["resultatTest"].strip().upper()
        etat_test = rapport["test"]["etatTest"]
        defaut = rapport.get("defaut")

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

        produit = rapport["produit"]
        operation = rapport["operation"]
        machine = rapport["machine"]
        test = rapport["test"]

        return RapportValide(
            id_rapport=rapport["idRapport"],
            pn=produit["pn"],
            sn=produit["sn"],
            type_produit=produit["type"],
            statut_produit=produit["statutProduit"],
            statut_carte=(produit.get("carte") or {}).get("statutCarte"),
            nombre_cartes_panel=(produit.get("panel") or {}).get("nombreCartes"),
            numero_of=rapport["of"]["numeroOF"],
            client=rapport["of"]["client"],
            quantite_of=rapport["of"]["quantite"],
            type_operation=operation["typeOperation"],
            numero_operation=operation.get("numeroOperation"),
            nom_operation=operation["nomOperation"],
            date_fin_operation_iso=(
                operation["dateFinOperation"].isoformat()
                if operation.get("dateFinOperation") else None
            ),
            code_machine=machine["codeMachine"],
            type_machine=machine["typeMachine"],
            codes_interfaces=[i["codeInterface"] for i in machine.get("interfaces", [])],
            face_test=test.get("face"),
            etat_test=test["etatTest"],
            resultat_test=test["resultatTest"],
            date_fin_test_iso=test["dateFinTest"].isoformat(),
            version_logiciel=test.get("versionLogiciel"),
            code_operateur=test.get("codeOperateur"),
            logs=rapport["logs"],
            defaut=defaut,
        )