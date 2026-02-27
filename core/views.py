from django.http import HttpResponse
from .models import OF, LogTest, Produit, ReferenceProduit, Test

def index(request):
    return HttpResponse("Hello, world. You're at the core index.")

def of_list(request):
    ofs = OF.objects.all().order_by("numeroOF")
    lines = [f"{of.numeroOF} - {of.client} - {of.idReferenceProduit} - {of.statutOF}" for of in ofs]
    return HttpResponse("<br>".join(lines))

def reference_list(request):
    references = ReferenceProduit.objects.all().order_by("PN")
    lines = [f"{ref.PN} - {ref.description}" for ref in references]
    return HttpResponse("<br>".join(lines))

def produit_list(request):
    produits = Produit.objects.all().order_by("SN")
    lines = [f"{prod.SN} - {prod.idReferenceProduit} - {prod.statutProduit}" for prod in produits]
    return HttpResponse("<br>".join(lines))

def logs_list(request):
    """
    Affiche tous les logs présents en base.
    """

    logs = LogTest.objects.all().order_by("-dateEtape")

    lignes = []

    for log in logs:
        lignes.append(
            f"""
            <div style="margin-bottom:15px;">
                <b>Test ID :</b> {log.idTest.idRapport}<br>
                <b>Étape :</b> {log.numeroEtape} - {log.nomEtape}<br>
                <b>Résultat :</b> {log.resultatEtape}<br>
                <b>Composant :</b> {log.composant}<br>
                <b>Face :</b> {log.face}<br>
                <b>Date :</b> {log.dateEtape}
            </div>
            <hr>
            """
        )

    return HttpResponse("".join(lignes))

def tests(request):
    """
    Affiche tous les tests en fonction de leur numéro de série.
    """

    tests = Test.objects.all().order_by("-dateFinTest")

    lignes = []

    for test in tests:
        lignes.append(
            f"""
            <div style="margin-bottom:15px;">
                <b>Test ID :</b> {test.idRapport}<br>
                <b>SN :</b> {test.idProduit.SN}<br>
                <b>Résultat :</b> {test.resultatTest}<br>
                <b>Date fin :</b> {test.dateFinTest}
            </div>
            <hr>
            """
        )

    return HttpResponse("".join(lignes))