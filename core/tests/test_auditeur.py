import pytest

from core.domain.auditeur import AuditeurRapport
from core.domain.exceptions import ErreurValidationMetier


def rapport_base_valide() -> dict:
    return {
        "idRapport": "RPT-2026-02-24-000999",
        "createdAt": "2026-02-24T09:30:12Z",
        "produit": {
            "type": "CARTE",
            "sn": "SN00123456",
            "pn": "PN-ABC-123",
            "statutProduit": "A_ANALYSER",
            "carte": {"statutCarte": "A_ANALYSER"},
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
            "interfaces": [{"codeInterface": "IF-01"}],
        },
        "test": {
            "face": "TOP",
            "etatTest": True,
            "resultatTest": "PASS",
            "dateFinTest": "2026-02-24T09:29:58Z",
            "versionLogiciel": "v2.3.1",
            "codeOperateur": None,
        },
        "logs": [
            {
                "numeroEtape": 10,
                "nomEtape": "Check",
                "resultatEtape": True,
                "dateEtape": "2026-02-24T09:29:10Z",
            }
        ],
        "defaut": None,
    }


def test_auditeur_accepte_rapport_valide():
    auditeur = AuditeurRapport()
    rapport = rapport_base_valide()

    resultat = auditeur.valider(rapport)

    assert resultat.id_rapport == rapport["idRapport"]
    assert resultat.numero_of == "4578965"


def test_auditeur_refuse_carte_sans_bloc_carte():
    auditeur = AuditeurRapport()
    rapport = rapport_base_valide()
    rapport["produit"]["carte"] = None

    with pytest.raises(ErreurValidationMetier):
        auditeur.valider(rapport)


def test_auditeur_refuse_etat_test_false_sans_defaut():
    auditeur = AuditeurRapport()
    rapport = rapport_base_valide()
    rapport["test"]["etatTest"] = False
    rapport["test"]["resultatTest"] = "FAIL"
    rapport["defaut"] = None

    with pytest.raises(ErreurValidationMetier):
        auditeur.valider(rapport)


def test_auditeur_refuse_etat_test_true_avec_resultat_non_pass():
    auditeur = AuditeurRapport()
    rapport = rapport_base_valide()
    rapport["test"]["etatTest"] = True
    rapport["test"]["resultatTest"] = "FAIL"

    with pytest.raises(ErreurValidationMetier):
        auditeur.valider(rapport)