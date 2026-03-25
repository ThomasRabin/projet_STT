import json
import pytest


@pytest.mark.django_db
def test_api_ingestion_ok(client):
    payload = {
        "idRapport": "RPT-AOI_01-20260325090000",
        "createdAt": "2025-10-14T15:06:10.000+02:00",
        "produit": {
            "type": "CARTE",
            "sn": "SN_API_1",
            "pn": "PN_API",
            "statutProduit": "A analyser",
            "carte": {"statutCarte": "A analyser"},
            "panel": None,
        },
        "of": {
            "numeroOF": "4578965",
            "client": "CLIENT_X",
            "quantite": 1,
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
            "versionLogiciel": "v1.0",
            "codeOperateur": None,
        },
        "logs": [
            {
                "dateEtape": "2025-10-14T15:05:00.000+02:00",
                "face": "TOP",
                "position": 1,
                "numeroEtape": 1,
                "nomEtape": "Step",
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

    url = "/core/ingestion/rapport/"
    response = client.post(
        url,
        data=json.dumps(payload),
        content_type="application/json",
    )

    body = response.json()

    assert response.status_code == 201
    assert body["statut"] == "OK"
    assert body["idRapport"] == payload["idRapport"]
    assert "message" in body


@pytest.mark.django_db
def test_api_ingestion_ko_json_invalide(client):
    url = "/core/ingestion/rapport/"
    response = client.post(
        url,
        data="{bad json",
        content_type="application/json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_api_ingestion_ko_regle_metier(client):
    payload = {
        "idRapport": "RPT-AOI_02-20260325090001",
        "createdAt": "2025-10-14T15:06:10.000+02:00",
        "produit": {
            "type": "CARTE",
            "sn": "SN_API_2",
            "pn": "PN_API",
            "statutProduit": "A analyser",
            "carte": {"statutCarte": "A analyser"},
            "panel": None,
        },
        "of": {
            "numeroOF": "4578966",
            "client": "CLIENT_X",
            "quantite": 1,
        },
        "operation": {
            "typeOperation": "TEST",
            "nomOperation": "AOI",
            "dateFinOperation": None,
            "numeroOperation": None,
        },
        "machine": {
            "codeMachine": "AOI-02",
            "typeMachine": "AOI",
            "interface": "IF-01",
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
                "nomEtape": "Step",
                "messageErreur": "Erreur test",
                "limMoins": None,
                "limPlus": None,
                "valeurMesuree": None,
                "unite": None,
                "resultatEtape": False,
                "composant": None,
                "refComposant": None,
            }
        ],
        "defaut": None,
    }

    url = "/core/ingestion/rapport/"
    response = client.post(
        url,
        data=json.dumps(payload),
        content_type="application/json",
    )

    body = response.json()

    assert response.status_code == 422
    assert body["statut"] == "KO"
    assert body["codeErreur"] == "BUSINESS_RULE_FAILED"