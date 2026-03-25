import pytest

from core.ingestion.serializers import RapportEntreeSerializer
from core.domain.auditeur import AuditeurRapport
from core.domain.exceptions import ErreurValidationMetier


def rapport_base_valide() -> dict:
    return {
        "idRapport": "RPT-AOI_01-20260325090010",
        "createdAt": "2025-10-14T15:06:10.000+02:00",
        "produit": {
            "type": "CARTE",
            "sn": "SN00123456",
            "pn": "PN-ABC-123",
            "statutProduit": "A analyser",
            "carte": {"statutCarte": "A analyser"},
            "panel": None,
        },
        "of": {
            "numeroOF": "4578965",
            "client": "CLIENT_X",
            "quantite": 120,
        },
        "operation": {
            "typeOperation": "TEST",
            "nomOperation": "AOI",
            "dateFinOperation": None,
            "numeroOperation": None,
        },
        "machine": {
            "codeMachine": "AOI-01",
            "typeMachine": "AOI",
            "interface": "IF-01",
        },
        "test": {
            "face": "TOP",
            "etatTest": True,
            "resultatTest": "PASS",
            "dateFinTest": "2025-10-14T15:06:10.000+02:00",
            "versionLogiciel": "v2.3.1",
            "codeOperateur": None,
        },
        "logs": [
            {
                "dateEtape": "2025-10-14T15:05:00.000+02:00",
                "face": "TOP",
                "position": 1,
                "numeroEtape": 10,
                "nomEtape": "Check",
                "messageErreur": None,
                "limMoins": None,
                "limPlus": None,
                "valeurMesuree": None,
                "unite": None,
                "resultatEtape": True,
                "composant": None,
                "refComposant": None,
            }
        ],
        "defaut": None,
    }


def valider_payload_par_serializer(payload: dict) -> dict:
    serializer = RapportEntreeSerializer(data=payload)
    assert serializer.is_valid(), serializer.errors
    return serializer.validated_data


def test_auditeur_accepte_rapport_valide():
    auditeur = AuditeurRapport()
    payload = rapport_base_valide()

    donnees_validees = valider_payload_par_serializer(payload)
    resultat = auditeur.valider(donnees_validees)

    assert resultat.id_rapport == payload["idRapport"]
    assert resultat.numero_of == "4578965"
    assert resultat.code_interface == "IF-01"


def test_auditeur_refuse_etat_test_false_sans_defaut():
    auditeur = AuditeurRapport()
    payload = rapport_base_valide()
    payload["test"]["etatTest"] = False
    payload["test"]["resultatTest"] = "FAIL"
    payload["defaut"] = None
    payload["logs"][0]["resultatEtape"] = False
    payload["logs"][0]["messageErreur"] = "Erreur"

    donnees_validees = valider_payload_par_serializer(payload)

    with pytest.raises(ErreurValidationMetier):
        auditeur.valider(donnees_validees)


def test_auditeur_refuse_etat_test_true_avec_resultat_non_pass():
    auditeur = AuditeurRapport()
    payload = rapport_base_valide()
    payload["test"]["etatTest"] = True
    payload["test"]["resultatTest"] = "FAIL"

    donnees_validees = valider_payload_par_serializer(payload)

    with pytest.raises(ErreurValidationMetier):
        auditeur.valider(donnees_validees)


def test_auditeur_refuse_position_diff_de_1_pour_carte():
    auditeur = AuditeurRapport()
    payload = rapport_base_valide()
    payload["logs"][0]["position"] = 2

    donnees_validees = valider_payload_par_serializer(payload)

    with pytest.raises(ErreurValidationMetier):
        auditeur.valider(donnees_validees)