"""
@file receptionneur.py
@brief Point d'entrée HTTP DRF pour la réception des rapports JSON.

@details
Ce module expose une vue Django REST Framework permettant de recevoir un
rapport de test au format JSON via HTTP POST.

Flux d'exécution global :
1) Vérification du Content-Type
2) Validation structurelle / typage via serializer DRF
3) Validation métier via AuditeurRapport
4) Persistance via GestionnairePersistance
5) Retour d'un acquittement JSON standardisé avec code HTTP adapté

Formats supportés :
- carte unitaire
- panel avec SN
- panel sans SN mais avec cartes
- panel avec cartes identifiées individuellement
"""

from __future__ import annotations

import traceback

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser
from rest_framework.response import Response

from core.domain.auditeur import AuditeurRapport
from core.domain.exceptions import (
    ErreurValidationMetier,
    ErreurConflitRapport,
    ErreurTechniqueTemporaire,
)
from core.ingestion.serializers import RapportEntreeSerializer
from core.services.gestionnairePersistance import GestionnairePersistance


def construire_acquittement(
    *,
    statut_metier: str,
    message: str,
    id_rapport: str | None = None,
    tentative: int | None = None,
    code_erreur: str | None = None,
    details: dict | list | None = None,
) -> dict:
    """
    @brief Construit le corps JSON standard de réponse API.

    @param statut_metier Statut métier parmi OK / RETRY / KO.
    @param message Message lisible et exploitable.
    @param id_rapport Identifiant rapport si disponible.
    @param tentative Numéro de tentative si applicable.
    @param code_erreur Code applicatif stable.
    @param details Détails complémentaires, typiquement serializer.errors.
    @return dict sérialisable en JSON.
    """
    payload = {
        "statut": statut_metier,
        "message": message,
        "horodatage": timezone.now().isoformat(),
    }

    if id_rapport is not None:
        payload["idRapport"] = id_rapport

    if tentative is not None:
        payload["tentative"] = tentative

    if code_erreur is not None:
        payload["codeErreur"] = code_erreur

    if details is not None:
        payload["details"] = details

    return payload


@api_view(["POST"])
@parser_classes([JSONParser])
def recevoir_rapport(request) -> Response:
    """
    @brief Reçoit, valide et persiste un rapport de test.

    @return Response
        - 201 Created : rapport accepté et persisté
        - 400 Bad Request : JSON invalide / structure invalide
        - 415 Unsupported Media Type : Content-Type non supporté
        - 422 Unprocessable Entity : règle métier non respectée
        - 409 Conflict : doublon / conflit de persistance
        - 503 Service Unavailable : erreur technique temporaire
        - 500 Internal Server Error : erreur imprévue
    """
    content_type = request.content_type or ""
    if not content_type.startswith("application/json"):
        return Response(
            construire_acquittement(
                statut_metier="KO",
                message="Content-Type non supporté, 'application/json' attendu",
                code_erreur="UNSUPPORTED_MEDIA_TYPE",
            ),
            status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )

    serializer = RapportEntreeSerializer(data=request.data)

    if not serializer.is_valid():
        id_rapport = None
        if isinstance(request.data, dict):
            id_rapport = request.data.get("idRapport")

        return Response(
            construire_acquittement(
                statut_metier="KO",
                message="Requête invalide",
                id_rapport=id_rapport,
                code_erreur="INVALID_REQUEST",
                details=serializer.errors,
            ),
            status=status.HTTP_400_BAD_REQUEST,
        )

    donnees_validees = serializer.validated_data
    id_rapport = donnees_validees.get("idRapport")

    auditeur = AuditeurRapport()
    persistance = GestionnairePersistance()

    try:
        rapport_valide = auditeur.valider(donnees_validees)
        persistance.persister(rapport_valide)

        return Response(
            construire_acquittement(
                statut_metier="OK",
                message="Rapport accepté et persisté",
                id_rapport=rapport_valide.id_rapport,
                code_erreur=None,
            ),
            status=status.HTTP_201_CREATED,
        )

    except ErreurValidationMetier as exc:
        return Response(
            construire_acquittement(
                statut_metier="KO",
                message=str(exc),
                id_rapport=id_rapport,
                code_erreur="BUSINESS_RULE_FAILED",
            ),
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    except ErreurConflitRapport as exc:
        return Response(
            construire_acquittement(
                statut_metier="KO",
                message=str(exc),
                id_rapport=id_rapport,
                code_erreur="REPORT_CONFLICT",
            ),
            status=status.HTTP_409_CONFLICT,
        )

    except ErreurTechniqueTemporaire as exc:
        return Response(
            construire_acquittement(
                statut_metier="RETRY",
                message=str(exc),
                id_rapport=id_rapport,
                code_erreur="TEMPORARY_TECHNICAL_ERROR",
            ),
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    except Exception as exc:
        traceback.print_exc()
        return Response(
            construire_acquittement(
                statut_metier="RETRY",
                message=str(exc),
                id_rapport=id_rapport,
                code_erreur="INTERNAL_ERROR",
            ),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )