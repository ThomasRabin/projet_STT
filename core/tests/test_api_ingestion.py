import json
import pytest


@pytest.mark.django_db
def test_api_ingestion_ok(client):
    payload = {
        "idRapport": "RPT-2026-02-24-200001",
        "produit": {
            "type": "CARTE",
            "sn": "SN_API_1",
            "pn": "PN_API",
            "statutProduit": "A_ANALYSER",
            "carte": {"statutCarte": "A_ANALYSER"},
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
            "interfaces": [],
        },
        "test": {
            "face": "TOP",
            "etatTest": True,
            "resultatTest": "PASS",
            "dateFinTest": "2026-02-24T09:29:58Z",
        },
        "logs": [
            {
                "numeroEtape": 1,
                "nomEtape": "Step",
                "resultatEtape": True,
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

    body = response.json()

    assert response.status_code == 400
    assert body["statut"] == "KO"
    assert body["codeErreur"] == "INVALID_REQUEST"


@pytest.mark.django_db
def test_api_ingestion_ko_regle_metier(client):
    payload = {
        "idRapport": "RPT-2026-02-24-200002",
        "produit": {
            "type": "CARTE",
            "sn": "SN_API_2",
            "pn": "PN_API",
            "statutProduit": "A_ANALYSER",
            "carte": {"statutCarte": "A_ANALYSER"},
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
            "interfaces": [],
        },
        "test": {
            "face": "TOP",
            "etatTest": False,
            "resultatTest": "FAIL",
            "dateFinTest": "2026-02-24T09:29:58Z",
        },
        "logs": [
            {
                "numeroEtape": 1,
                "nomEtape": "Step",
                "resultatEtape": False,
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