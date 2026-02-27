"""
@file receptionneur.py
@brief Point d'entrée HTTP pour la réception des rapports de test au format JSON.

@details
Ce module expose une vue Django permettant de recevoir un rapport de test
au format JSON via une requête HTTP POST.

Flux d'exécution global :

1) Réception de la requête HTTP.
2) Décodage du corps brut (bytes → UTF-8 string).
3) Désérialisation JSON (string → dict Python).
4) Validation structurelle et métier via @ref AuditeurRapport.
5) Persistance en base via @ref GestionnairePersistance.
6) Retour d'une réponse JSON standardisée.

Architecture respectée :
- Ingestion (HTTP) : ce module
- Validation métier : core.domain.auditeur
- Persistance : core.services.gestionnairePersistance

@note
Cette vue est exemptée de CSRF car elle est destinée à être appelée
par un système externe (ETL / machine / API industrielle).
"""

import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.domain.auditeur import AuditeurRapport
from core.domain.exceptions import ErreurValidationRapport
from core.services.gestionnairePersistance import GestionnairePersistance


@csrf_exempt
@require_POST
def recevoir_rapport(request):
    """
    @brief Point d'entrée HTTP pour la réception d'un rapport de test.

    @details
    Cette fonction est appelée lorsqu'un client envoie une requête POST
    contenant un rapport JSON.

    Étapes :
    - Lecture du corps brut de la requête (request.body).
    - Décodage UTF-8.
    - Parsing JSON vers dictionnaire Python.
    - Validation via @ref AuditeurRapport.
    - Persistance via @ref GestionnairePersistance.
    - Retour d'un statut HTTP approprié.

    @param request Objet HttpRequest Django contenant le JSON dans request.body.
    @return JsonResponse :
        - 201 si le rapport est valide et persisté.
        - 400 si le JSON est invalide.
        - 400 si la validation métier échoue.

    @raises ErreurValidationRapport
        Interceptée localement pour retourner une erreur métier propre.
    """

    # ==============================
    # 1) Décodage et parsing JSON
    # ==============================
    try:
        # Corps brut en bytes → conversion en string UTF-8
        texte_json = request.body.decode("utf-8")

        # Conversion du texte JSON en dictionnaire Python
        rapport_dict = json.loads(texte_json)

    except Exception:
        # JSON mal formé ou encodage incorrect
        return JsonResponse(
            {"ok": False, "error": "JSON invalide"},
            status=400
        )

    # ==============================
    # 2) Instanciation des services
    # ==============================
    auditeur = AuditeurRapport()
    persistance = GestionnairePersistance()

    # ==============================
    # 3) Validation métier
    # ==============================
    try:
        rapport_valide = auditeur.valider(rapport_dict)

    except ErreurValidationRapport as erreur:
        # Erreur de cohérence métier ou structure invalide
        return JsonResponse(
            {"ok": False, "error": str(erreur)},
            status=400
        )

    # ==============================
    # 4) Persistance en base
    # ==============================
    persistance.persister(rapport_valide)

    # ==============================
    # 5) Réponse succès
    # ==============================
    return JsonResponse(
        {"ok": True, "idRapport": rapport_valide.id_rapport},
        status=201
    )