import pytest

from core.domain.auditeur import AuditeurRapport
from core.services.gestionnairePersistance import GestionnairePersistance
from core.models import (
    ReferenceProduit,
    OF,
    Produit,
    AffectationProduitOF,
    Machine,
    InterfaceMachine,
    PassageTest,
    LogTest,
)


@pytest.mark.django_db
def test_persistance_cree_tout():
    auditeur = AuditeurRapport()
    service = GestionnairePersistance()

    rapport = {
        "idRapport": "RPT-2026-02-24-100001",
        "produit": {
            "type": "CARTE",
            "sn": "SN_TEST_1",
            "pn": "PN_TEST",
            "statutProduit": "A_ANALYSER",
            "carte": {"statutCarte": "A_ANALYSER"},
            "panel": None,
        },
        "of": {
            "numeroOF": "4578965",
            "client": "CLIENT_X",
            "quantite": 10,
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
                "numeroEtape": 1,
                "nomEtape": "Step1",
                "resultatEtape": True,
                "dateEtape": "2026-02-24T09:29:10Z",
            }
        ],
        "defaut": None,
    }

    rapport_valide = auditeur.valider(rapport)
    service.persister(rapport_valide)

    assert ReferenceProduit.objects.filter(PN="PN_TEST").exists()
    assert OF.objects.filter(numeroOF="4578965").exists()
    assert Produit.objects.filter(SN="SN_TEST_1").exists()
    assert Machine.objects.filter(codeMachine="AOI-01").exists()
    assert InterfaceMachine.objects.filter(codeInterface="IF-01").exists()

    test_obj = PassageTest.objects.get(idRapport="RPT-2026-02-24-100001")
    assert test_obj.FPY_flag is True
    assert LogTest.objects.filter(idTest=test_obj).count() == 1

    produit = Produit.objects.get(SN="SN_TEST_1")
    assert AffectationProduitOF.objects.filter(idProduit=produit).count() == 1


@pytest.mark.django_db
def test_persistance_idempotence_affectation_of():
    auditeur = AuditeurRapport()
    service = GestionnairePersistance()

    rapport = {
        "idRapport": "RPT-2026-02-24-100002",
        "produit": {
            "type": "CARTE",
            "sn": "SN_TEST_2",
            "pn": "PN_TEST",
            "statutProduit": "A_ANALYSER",
            "carte": {"statutCarte": "A_ANALYSER"},
            "panel": None,
        },
        "of": {
            "numeroOF": "4578965",
            "client": "CLIENT_X",
            "quantite": 10,
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
            "interfaces": [],
        },
        "test": {
            "face": "TOP",
            "etatTest": True,
            "resultatTest": "PASS",
            "dateFinTest": "2026-02-24T09:29:58Z",
            "versionLogiciel": None,
            "codeOperateur": None,
        },
        "logs": [
            {
                "numeroEtape": 1,
                "nomEtape": "Step1",
                "resultatEtape": True,
            }
        ],
        "defaut": None,
    }

    service.persister(auditeur.valider(rapport))

    rapport2 = dict(rapport)
    rapport2["idRapport"] = "RPT-2026-02-24-100003"
    service.persister(auditeur.valider(rapport2))

    produit = Produit.objects.get(SN="SN_TEST_2")
    assert AffectationProduitOF.objects.filter(idProduit=produit).count() == 1


@pytest.mark.django_db
def test_persistance_calcule_fpy_false_si_deuxieme_passage():
    auditeur = AuditeurRapport()
    service = GestionnairePersistance()

    rapport_1 = {
        "idRapport": "RPT-2026-02-24-100010",
        "produit": {
            "type": "CARTE",
            "sn": "SN_FPY_1",
            "pn": "PN_FPY",
            "statutProduit": "A_ANALYSER",
            "carte": {"statutCarte": "A_ANALYSER"},
            "panel": None,
        },
        "of": {
            "numeroOF": "1111111",
            "client": "CLIENT_FPY",
            "quantite": 10,
        },
        "operation": {
            "typeOperation": "TEST",
            "nomOperation": "ICT",
            "dateFinOperation": None,
            "numeroOperation": None,
        },
        "machine": {
            "codeMachine": "ICT-01",
            "typeMachine": "ICT",
            "interfaces": [],
        },
        "test": {
            "face": "TOP",
            "etatTest": False,
            "resultatTest": "FAIL",
            "dateFinTest": "2026-02-24T09:29:58Z",
            "versionLogiciel": None,
            "codeOperateur": None,
        },
        "logs": [
            {
                "numeroEtape": 1,
                "nomEtape": "Step1",
                "resultatEtape": False,
            }
        ],
        "defaut": {
            "numeroDefaut": 1,
            "nomDefaut": "Defaut test",
            "dateDefaut": "2026-02-24T09:30:00Z",
            "dateRework": None,
            "commentaireDefaut": "Premier passage KO",
        },
    }

    rapport_2 = {
        **rapport_1,
        "idRapport": "RPT-2026-02-24-100011",
        "test": {
            "face": "TOP",
            "etatTest": True,
            "resultatTest": "PASS",
            "dateFinTest": "2026-02-24T10:29:58Z",
            "versionLogiciel": None,
            "codeOperateur": None,
        },
        "logs": [
            {
                "numeroEtape": 1,
                "nomEtape": "Step1",
                "resultatEtape": True,
            }
        ],
        "defaut": None,
    }

    service.persister(auditeur.valider(rapport_1))
    service.persister(auditeur.valider(rapport_2))

    test_1 = PassageTest.objects.get(idRapport="RPT-2026-02-24-100010")
    test_2 = PassageTest.objects.get(idRapport="RPT-2026-02-24-100011")

    assert test_1.FPY_flag is False
    assert test_2.FPY_flag is False