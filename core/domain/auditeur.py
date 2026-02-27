from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from django.utils.dateparse import parse_datetime

from .exceptions import ErreurValidationRapport
from .types_rapport import CHAMPS_OBLIGATOIRES


def lire_champ_obligatoire(donnees: dict, chemin: str) -> Any:
    """
    Lit un champ obligatoire via un chemin type "produit.sn".
    - si la clé est absente à un niveau -> ErreurValidationRapport
    """
    dictionnaire_courant: Any = donnees
    niveaux = chemin.split(".")

    for nom_du_niveau in niveaux:
        if not isinstance(dictionnaire_courant, dict) or nom_du_niveau not in dictionnaire_courant:
            raise ErreurValidationRapport(f"Champ obligatoire manquant : {chemin}")
        dictionnaire_courant = dictionnaire_courant[nom_du_niveau]

    return dictionnaire_courant


def lire_champ_optionnel(donnees: dict, chemin: str) -> Any:
    """
    Lit un champ optionnel. Si absent -> None.
    """
    dictionnaire_courant: Any = donnees
    niveaux = chemin.split(".")

    for nom_du_niveau in niveaux:
        if not isinstance(dictionnaire_courant, dict) or nom_du_niveau not in dictionnaire_courant:
            return None
        dictionnaire_courant = dictionnaire_courant[nom_du_niveau]

    return dictionnaire_courant


@dataclass(frozen=True)
class RapportValide:
    """
    Représentation "validée" du rapport, prête à être persistée.
    On garde des noms explicites et des types cohérents.
    """
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
    nom_operation: str
    date_fin_operation_iso: str

    code_machine: str
    type_machine: str
    codes_interfaces: list[str]

    face_test: Optional[str]
    etat_test: bool
    resultat_test: str
    fpy_flag: bool
    date_fin_test_iso: str
    version_logiciel: Optional[str]
    code_operateur: Optional[int]

    logs: list[dict]
    defaut: Optional[dict]


class AuditeurRapport:
    """
    Valide un rapport JSON (dict Python) et renvoie un RapportValide.
    """

    def valider(self, rapport: dict) -> RapportValide:
        # 1) Vérifier les champs obligatoires "structurels"
        for chemin in CHAMPS_OBLIGATOIRES:
            lire_champ_obligatoire(rapport, chemin)

        # 2) Extraire les valeurs utiles
        id_rapport = lire_champ_obligatoire(rapport, "idRapport")

        type_produit = lire_champ_obligatoire(rapport, "produit.type")
        sn = lire_champ_obligatoire(rapport, "produit.sn")
        pn = lire_champ_obligatoire(rapport, "produit.pn")
        statut_produit = lire_champ_obligatoire(rapport, "produit.statutProduit")

        # Règle métier : si CARTE => produit.carte doit exister, si PANEL => produit.panel doit exister
        bloc_carte = lire_champ_optionnel(rapport, "produit.carte")
        bloc_panel = lire_champ_optionnel(rapport, "produit.panel")

        statut_carte: Optional[str] = None
        nombre_cartes_panel: Optional[int] = None

        if type_produit == "CARTE":
            if bloc_carte is None:
                raise ErreurValidationRapport("produit.type=CARTE mais produit.carte est absent/null")
            statut_carte = lire_champ_obligatoire(rapport, "produit.carte.statutCarte")
            if bloc_panel is not None:
                raise ErreurValidationRapport("produit.type=CARTE mais produit.panel n'est pas null")
        elif type_produit == "PANEL":
            if bloc_panel is None:
                raise ErreurValidationRapport("produit.type=PANEL mais produit.panel est absent/null")
            nombre_cartes_panel = lire_champ_obligatoire(rapport, "produit.panel.nombreCartes")
            if bloc_carte is not None:
                raise ErreurValidationRapport("produit.type=PANEL mais produit.carte n'est pas null")
        else:
            raise ErreurValidationRapport("produit.type doit être 'CARTE' ou 'PANEL'")

        numero_of = lire_champ_obligatoire(rapport, "of.numeroOF")
        client = lire_champ_obligatoire(rapport, "of.client")
        quantite_of = lire_champ_obligatoire(rapport, "of.quantite")

        type_operation = lire_champ_obligatoire(rapport, "operation.typeOperation")
        nom_operation = lire_champ_obligatoire(rapport, "operation.nomOperation")
        date_fin_operation_iso = lire_champ_obligatoire(rapport, "operation.dateFinOperation")

        # Vérifier que la date est parseable ISO
        if parse_datetime(date_fin_operation_iso) is None:
            raise ErreurValidationRapport("operation.dateFinOperation n'est pas une date ISO valide")

        code_machine = lire_champ_obligatoire(rapport, "machine.codeMachine")
        type_machine = lire_champ_obligatoire(rapport, "machine.typeMachine")

        interfaces = lire_champ_optionnel(rapport, "machine.interfaces") or []
        if not isinstance(interfaces, list):
            raise ErreurValidationRapport("machine.interfaces doit être une liste")

        codes_interfaces: list[str] = []
        for interface in interfaces:
            if not isinstance(interface, dict) or "codeInterface" not in interface:
                raise ErreurValidationRapport("Chaque interface doit contenir codeInterface")
            codes_interfaces.append(interface["codeInterface"])

        face_test = lire_champ_optionnel(rapport, "test.face")
        etat_test = lire_champ_obligatoire(rapport, "test.etatTest")
        resultat_test = lire_champ_obligatoire(rapport, "test.resultatTest")
        fpy_flag = lire_champ_obligatoire(rapport, "test.fpyFlag")
        date_fin_test_iso = lire_champ_obligatoire(rapport, "test.dateFinTest")
        version_logiciel = lire_champ_optionnel(rapport, "test.versionLogiciel")
        code_operateur = lire_champ_optionnel(rapport, "test.codeOperateur")

        if parse_datetime(date_fin_test_iso) is None:
            raise ErreurValidationRapport("test.dateFinTest n'est pas une date ISO valide")

        logs = lire_champ_obligatoire(rapport, "logs")
        if not isinstance(logs, list):
            raise ErreurValidationRapport("logs doit être une liste")

        defaut = lire_champ_optionnel(rapport, "defaut")

        return RapportValide(
            id_rapport=id_rapport,
            pn=pn,
            sn=sn,
            type_produit=type_produit,
            statut_produit=statut_produit,
            statut_carte=statut_carte,
            nombre_cartes_panel=nombre_cartes_panel,
            numero_of=numero_of,
            client=client,
            quantite_of=int(quantite_of),
            type_operation=type_operation,
            nom_operation=nom_operation,
            date_fin_operation_iso=date_fin_operation_iso,
            code_machine=code_machine,
            type_machine=type_machine,
            codes_interfaces=codes_interfaces,
            face_test=face_test,
            etat_test=bool(etat_test),
            resultat_test=resultat_test,
            fpy_flag=bool(fpy_flag),
            date_fin_test_iso=date_fin_test_iso,
            version_logiciel=version_logiciel,
            code_operateur=code_operateur,
            logs=logs,
            defaut=defaut,
        )