from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from django.utils.dateparse import parse_datetime

from .exceptions import ErreurValidationRapport
from .types_rapport import CHAMPS_OBLIGATOIRES


def lire_champ_obligatoire(donnees: dict, chemin: str) -> Any:
    dictionnaire_courant: Any = donnees
    niveaux = chemin.split(".")

    for nom_du_niveau in niveaux:
        if (
            not isinstance(dictionnaire_courant, dict)
            or nom_du_niveau not in dictionnaire_courant
        ):
            raise ErreurValidationRapport(f"Champ obligatoire manquant : {chemin}")
        dictionnaire_courant = dictionnaire_courant[nom_du_niveau]

    return dictionnaire_courant


def lire_champ_optionnel(donnees: dict, chemin: str) -> Any:
    dictionnaire_courant: Any = donnees
    niveaux = chemin.split(".")

    for nom_du_niveau in niveaux:
        if (
            not isinstance(dictionnaire_courant, dict)
            or nom_du_niveau not in dictionnaire_courant
        ):
            return None
        dictionnaire_courant = dictionnaire_courant[nom_du_niveau]

    return dictionnaire_courant


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
    nom_operation: str
    date_fin_operation_iso: Optional[str]

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
    Inclut aussi des règles métier (cohérence) en plus du typage.
    """

    # Valeurs autorisées (copiées depuis tes choices Django)
    STATUTS_PRODUIT_AUTORISES = {"OK", "A_ANALYSER", "A_REPARER", "A_RETESTER", "REBUTER"}
    TYPES_OPERATION_AUTORISES = {"AUTOMATIQUE", "MANUELLE", "TEST", "CONTROLE"}
    TYPES_MACHINE_AUTORISES = {
        "CMS",
        "VAGUE",
        "AOI",
        "ICT",
        "FCT",
        "PROGRAMMATION",
        "VRT",
        "AUTRE",
    }
    FACES_AUTORISEES = {"TOP", "BOTTOM"}

    def valider(self, rapport: dict) -> RapportValide:
        # 1) Structure minimale
        for chemin in CHAMPS_OBLIGATOIRES:
            lire_champ_obligatoire(rapport, chemin)

        id_rapport = lire_champ_obligatoire(rapport, "idRapport")

        # Optionnels racine (on ne force pas)
        created_at = lire_champ_optionnel(rapport, "createdAt")
        if created_at is not None and parse_datetime(created_at) is None:
            raise ErreurValidationRapport("createdAt n'est pas une date ISO valide")

        # 2) Produit
        type_produit = lire_champ_obligatoire(rapport, "produit.type")
        sn = lire_champ_obligatoire(rapport, "produit.sn")
        pn = lire_champ_obligatoire(rapport, "produit.pn")
        statut_produit = lire_champ_obligatoire(rapport, "produit.statutProduit")

        if statut_produit not in self.STATUTS_PRODUIT_AUTORISES:
            raise ErreurValidationRapport(
                f"produit.statutProduit invalide: {statut_produit}"
            )

        bloc_carte = lire_champ_optionnel(rapport, "produit.carte")
        bloc_panel = lire_champ_optionnel(rapport, "produit.panel")

        statut_carte: Optional[str] = None
        nombre_cartes_panel: Optional[int] = None

        if type_produit == "CARTE":
            if bloc_carte is None:
                raise ErreurValidationRapport(
                    "produit.type=CARTE mais produit.carte est absent/null"
                )
            if bloc_panel is not None:
                raise ErreurValidationRapport(
                    "produit.type=CARTE mais produit.panel n'est pas null"
                )

            statut_carte = lire_champ_obligatoire(rapport, "produit.carte.statutCarte")
            if statut_carte not in self.STATUTS_PRODUIT_AUTORISES:
                raise ErreurValidationRapport(
                    f"produit.carte.statutCarte invalide: {statut_carte}"
                )

        elif type_produit == "PANEL":
            if bloc_panel is None:
                raise ErreurValidationRapport(
                    "produit.type=PANEL mais produit.panel est absent/null"
                )
            if bloc_carte is not None:
                raise ErreurValidationRapport(
                    "produit.type=PANEL mais produit.carte n'est pas null"
                )

            nombre_cartes_panel = lire_champ_obligatoire(
                rapport, "produit.panel.nombreCartes"
            )
            try:
                nombre_cartes_panel = int(nombre_cartes_panel)
            except (TypeError, ValueError):
                raise ErreurValidationRapport("produit.panel.nombreCartes doit etre un entier")

            if nombre_cartes_panel <= 0:
                raise ErreurValidationRapport(
                    "produit.panel.nombreCartes doit etre > 0"
                )
        else:
            raise ErreurValidationRapport("produit.type doit etre 'CARTE' ou 'PANEL'")

        # 3) OF
        numero_of = lire_champ_obligatoire(rapport, "of.numeroOF")
        client = lire_champ_obligatoire(rapport, "of.client")
        quantite_of = lire_champ_obligatoire(rapport, "of.quantite")

        if not isinstance(numero_of, str) or len(numero_of) != 7 or not numero_of.isdigit():
            raise ErreurValidationRapport("of.numeroOF doit etre une chaîne de 7 chiffres")

        try:
            quantite_of = int(quantite_of)
        except (TypeError, ValueError):
            raise ErreurValidationRapport("of.quantite doit etre un entier")

        if quantite_of < 0:
            raise ErreurValidationRapport("of.quantite ne peut pas etre negative")

        # 4) Operation
        type_operation = lire_champ_obligatoire(rapport, "operation.typeOperation")
        nom_operation = lire_champ_obligatoire(rapport, "operation.nomOperation")
        date_fin_operation_iso = lire_champ_optionnel(rapport, "operation.dateFinOperation")

        if type_operation not in self.TYPES_OPERATION_AUTORISES:
            raise ErreurValidationRapport(
                f"operation.typeOperation invalide: {type_operation}"
            )

        if date_fin_operation_iso is not None and parse_datetime(date_fin_operation_iso) is None:
            raise ErreurValidationRapport("operation.dateFinOperation n'est pas une date ISO valide")

        # 5) Machine
        code_machine = lire_champ_obligatoire(rapport, "machine.codeMachine")
        type_machine = lire_champ_obligatoire(rapport, "machine.typeMachine")

        if type_machine not in self.TYPES_MACHINE_AUTORISES:
            raise ErreurValidationRapport(f"machine.typeMachine invalide: {type_machine}")

        interfaces = lire_champ_optionnel(rapport, "machine.interfaces") or []
        if not isinstance(interfaces, list):
            raise ErreurValidationRapport("machine.interfaces doit etre une liste")

        codes_interfaces: list[str] = []
        for interface in interfaces:
            if not isinstance(interface, dict) or "codeInterface" not in interface:
                raise ErreurValidationRapport("Chaque interface doit contenir codeInterface")
            code_interface = interface["codeInterface"]
            if not isinstance(code_interface, str) or not code_interface.strip():
                raise ErreurValidationRapport("codeInterface doit etre une chaine non vide")
            codes_interfaces.append(code_interface)

        # 6) Test
        face_test = lire_champ_optionnel(rapport, "test.face")
        etat_test = lire_champ_obligatoire(rapport, "test.etatTest")
        resultat_test = lire_champ_obligatoire(rapport, "test.resultatTest")
        fpy_flag = lire_champ_obligatoire(rapport, "test.fpyFlag")
        date_fin_test_iso = lire_champ_obligatoire(rapport, "test.dateFinTest")

        version_logiciel = lire_champ_optionnel(rapport, "test.versionLogiciel")
        code_operateur = lire_champ_optionnel(rapport, "test.codeOperateur")

        # Typage booleen (si ETL envoie "true"/"false" string, adapte ici)
        etat_test_bool = bool(etat_test)
        fpy_flag_bool = bool(fpy_flag)

        if face_test is not None:
            if face_test not in self.FACES_AUTORISEES:
                raise ErreurValidationRapport("test.face doit etre TOP ou BOTTOM")

        if parse_datetime(date_fin_test_iso) is None:
            raise ErreurValidationRapport("test.dateFinTest n'est pas une date ISO valide")

        # 7) Logs
        logs = lire_champ_obligatoire(rapport, "logs")
        if not isinstance(logs, list):
            raise ErreurValidationRapport("logs doit etre une liste")
        if len(logs) == 0:
            raise ErreurValidationRapport("logs ne doit pas etre vide")

        # 8) Defaut + cohérence PASS/FAIL
        defaut = lire_champ_optionnel(rapport, "defaut")

        resultat_test_str = str(resultat_test).upper().strip()

        if etat_test_bool is True:
            # Un test OK doit être PASS (ou contenir PASS)
            if "PASS" not in resultat_test_str:
                raise ErreurValidationRapport(
                    "etatTest=True mais resultatTest n'indique pas PASS"
                )
            # FPY true => forcément OK
            if fpy_flag_bool is True and etat_test_bool is not True:
                raise ErreurValidationRapport("fpyFlag=True mais etatTest n'est pas True")
        else:
            # Un test FAIL ne doit pas être PASS et doit avoir un défaut
            if "PASS" in resultat_test_str:
                raise ErreurValidationRapport(
                    "etatTest=False mais resultatTest contient PASS"
                )
            if defaut is None:
                raise ErreurValidationRapport(
                    "etatTest=False mais defaut est absent/null"
                )

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
            quantite_of=quantite_of,
            type_operation=type_operation,
            nom_operation=nom_operation,
            date_fin_operation_iso=date_fin_operation_iso,
            code_machine=code_machine,
            type_machine=type_machine,
            codes_interfaces=codes_interfaces,
            face_test=face_test,
            etat_test=etat_test_bool,
            resultat_test=resultat_test,
            fpy_flag=fpy_flag_bool,
            date_fin_test_iso=date_fin_test_iso,
            version_logiciel=version_logiciel,
            code_operateur=code_operateur,
            logs=logs,
            defaut=defaut,
        )