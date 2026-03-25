import pytest

from core.ingestion.serializers import RapportEntreeSerializer
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


def valider_payload_par_serializer(payload: dict) -> dict:
    serializer = RapportEntreeSerializer(data=payload)
    assert serializer.is_valid(), serializer.errors
    return serializer.validated_data


@pytest.mark.django_db
def test_persistance_cree_tout():
    auditeur = AuditeurRapport()
    service = GestionnairePersistance()

    payload = {
        "idRapport": "RPT-AOI_01-20260325090100",
        "createdAt": "2025-10-14T15:06:10.000+02:00",
        "produit": {
            "type": "CARTE",
            "sn": "SN_TEST_1",
            "pn": "PN_TEST",
            "statutProduit": "A analyser",
            "carte": {"statutCarte": "A analyser"},
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
                "numeroEtape": 1,
                "nomEtape": "Step1",
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

    donnees_validees = valider_payload_par_serializer(payload)
    rapport_valide = auditeur.valider(donnees_validees)
    service.persister(rapport_valide)

    assert ReferenceProduit.objects.filter(PN="PN_TEST").exists()
    assert OF.objects.filter(numeroOF="4578965").exists()
    assert Produit.objects.filter(SN="SN_TEST_1").exists()
    assert Machine.objects.filter(codeMachine="AOI-01").exists()
    assert InterfaceMachine.objects.filter(codeInterface="IF-01").exists()

    test_obj = PassageTest.objects.get(idRapport="RPT-AOI_01-20260325090100")
    assert test_obj.FPY_flag is True
    assert LogTest.objects.filter(idTest=test_obj).count() == 1

    produit = Produit.objects.get(SN="SN_TEST_1")
    assert AffectationProduitOF.objects.filter(idProduit=produit).count() == 1


@pytest.mark.django_db
def test_persistance_idempotence_affectation_of():
    auditeur = AuditeurRapport()
    service = GestionnairePersistance()

    payload = {
        "idRapport": "RPT-AOI_01-20260325090200",
        "createdAt": "2025-10-14T15:06:10.000+02:00",
        "produit": {
            "type": "CARTE",
            "sn": "SN_TEST_2",
            "pn": "PN_TEST",
            "statutProduit": "A analyser",
            "carte": {"statutCarte": "A analyser"},
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
            "interface": "IF-01",
        },
        "test": {
            "face": "TOP",
            "etatTest": True,
            "resultatTest": "PASS",
            "dateFinTest": "2025-10-14T15:06:10.000+02:00",
            "versionLogiciel": None,
            "codeOperateur": None,
        },
        "logs": [
            {
                "dateEtape": "2025-10-14T15:05:00.000+02:00",
                "face": "TOP",
                "position": 1,
                "numeroEtape": 1,
                "nomEtape": "Step1",
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

    donnees_validees_1 = valider_payload_par_serializer(payload)
    service.persister(auditeur.valider(donnees_validees_1))

    payload_2 = payload.copy()
    payload_2["idRapport"] = "RPT-AOI_01-20260325090201"

    donnees_validees_2 = valider_payload_par_serializer(payload_2)
    service.persister(auditeur.valider(donnees_validees_2))

    produit = Produit.objects.get(SN="SN_TEST_2")
    assert AffectationProduitOF.objects.filter(idProduit=produit).count() == 1


@pytest.mark.django_db
def test_persistance_calcule_fpy_false_si_deuxieme_passage():
    auditeur = AuditeurRapport()
    service = GestionnairePersistance()

    payload_1 = {
        "idRapport": "RPT-ICT_01-20260325090300",
        "createdAt": "2025-10-14T15:06:10.000+02:00",
        "produit": {
            "type": "CARTE",
            "sn": "SN_FPY_1",
            "pn": "PN_FPY",
            "statutProduit": "A analyser",
            "carte": {"statutCarte": "A analyser"},
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
            "interface": "IF-03",
        },
        "test": {
            "face": "TOP",
            "etatTest": False,
            "resultatTest": "FAIL",
            "dateFinTest": "2025-10-14T15:06:10.000+02:00",
            "versionLogiciel": None,
            "codeOperateur": None,
        },
        "logs": [
            {
                "dateEtape": "2025-10-14T15:05:00.000+02:00",
                "face": "TOP",
                "position": 1,
                "numeroEtape": 1,
                "nomEtape": "Step1",
                "messageErreur": "Premier passage KO",
                "limMoins": None,
                "limPlus": None,
                "valeurMesuree": None,
                "unite": None,
                "resultatEtape": False,
                "composant": None,
                "refComposant": None,
            }
        ],
        "defaut": {
            "numeroDefaut": 1,
            "nomDefaut": "Defaut test",
            "dateDefaut": "2025-10-14T15:06:10.000+02:00",
            "dateRework": None,
            "commentaireDefaut": "Premier passage KO",
        },
    }

    payload_2 = {
        **payload_1,
        "idRapport": "RPT-ICT_01-20260325090301",
        "test": {
            "face": "TOP",
            "etatTest": True,
            "resultatTest": "PASS",
            "dateFinTest": "2025-10-14T16:06:10.000+02:00",
            "versionLogiciel": None,
            "codeOperateur": None,
        },
        "logs": [
            {
                "dateEtape": "2025-10-14T16:05:00.000+02:00",
                "face": "TOP",
                "position": 1,
                "numeroEtape": 1,
                "nomEtape": "Step1",
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

    donnees_validees_1 = valider_payload_par_serializer(payload_1)
    donnees_validees_2 = valider_payload_par_serializer(payload_2)

    service.persister(auditeur.valider(donnees_validees_1))
    service.persister(auditeur.valider(donnees_validees_2))

    test_1 = PassageTest.objects.get(idRapport="RPT-ICT_01-20260325090300")
    test_2 = PassageTest.objects.get(idRapport="RPT-ICT_01-20260325090301")

    assert test_1.FPY_flag is False
    assert test_2.FPY_flag is False