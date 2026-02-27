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
    Point d'entrée HTTP qui reçoit le JSON de rapport.
    """
    try:
        texte_json = request.body.decode("utf-8") # Décode le JSON brut en texte
        rapport_dict = json.loads(texte_json) # Convertit le texte JSON en dictionnaire Python
    except Exception:
        return JsonResponse({"ok": False, "error": "JSON invalide"}, status=400)

    auditeur = AuditeurRapport()
    persistance = GestionnairePersistance()

    try:
        rapport_valide = auditeur.valider(rapport_dict)
    except ErreurValidationRapport as erreur:
        return JsonResponse({"ok": False, "error": str(erreur)}, status=400)

    persistance.persister(rapport_valide)
    return JsonResponse({"ok": True}, status=201)