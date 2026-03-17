import pytest

from core.domain.auditeur import AuditeurRapport
from core.services.gestionnairePersistance import GestionnairePersistance
from core.models import (
    ReferenceProduit, OF, Produit, AffectationProduitOF,
    Machine, InterfaceMachine, Operation, PassageTest, LogTest
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
        "of": {"numeroOF": "4578965", "client": "CLIENT_X", "quantite": 10},
        "operation": {"typeOperation": "TEST", "nomOperation": "AOI", "dateFinOperation": None, "numeroOperation": None},
        "machine": {"codeMachine": "AOI-01", "typeMachine": "AOI", "interfaces": [{"codeInterface": "IF-01"}]},
        "test": {
            "face": "TOP",
            "etatTest": True,
            "resultatTest": "PASS",
            "fpyFlag": True,
            "dateFinTest": "2026-02-24T09:29:58Z",
            "versionLogiciel": "v2.3.1",
            "codeOperateur": None,
        },
        "logs": [{"numeroEtape": 1, "nomEtape": "Step1", "resultatEtape": True, "dateEtape": "2026-02-24T09:29:10Z"}],
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
    assert LogTest.objects.filter(idTest=test_obj).count() == 1

    # Affectation créée
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
        "of": {"numeroOF": "4578965", "client": "CLIENT_X", "quantite": 10},
        "operation": {"typeOperation": "TEST", "nomOperation": "AOI", "dateFinOperation": None, "numeroOperation": None},
        "machine": {"codeMachine": "AOI-01", "typeMachine": "AOI", "interfaces": []},
        "test": {
            "face": "TOP",
            "etatTest": True,
            "resultatTest": "PASS",
            "fpyFlag": True,
            "dateFinTest": "2026-02-24T09:29:58Z",
            "versionLogiciel": None,
            "codeOperateur": None,
        },
        "logs": [{"numeroEtape": 1, "nomEtape": "Step1", "resultatEtape": True}],
        "defaut": None,
    }

    # 1er passage
    service.persister(auditeur.valider(rapport))
    # 2e passage (rapport différent mais même produit même OF)
    rapport2 = dict(rapport)
    rapport2["idRapport"] = "RPT-2026-02-24-100003"
    service.persister(auditeur.valider(rapport2))

    produit = Produit.objects.get(SN="SN_TEST_2")
    # Toujours 1 affectation car même OF
    assert AffectationProduitOF.objects.filter(idProduit=produit).count() == 1