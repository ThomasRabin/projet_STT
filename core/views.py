from django.http import HttpResponse
from django.utils import timezone

from .models import OF, LogTest, Produit, ReferenceProduit, PassageTest

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
    tests = PassageTest.objects.all().order_by("-dateFinTest")

    lignes = []

    for test in tests:
        if test.dateFinTest:
            date_locale = timezone.localtime(test.dateFinTest)
            date_formattee = date_locale.strftime("%d/%m/%Y %H:%M:%S")
        else:
            date_formattee = "N/A"

        lignes.append(
            f"""
            <div style="margin-bottom:15px;">
                <b>Test ID :</b> {test.idRapport}<br>
                <b>SN :</b> {test.idProduit.SN}<br>
                <b>Résultat :</b> {test.resultatTest}<br>
                <b>Date fin :</b> {date_formattee}<br>
                <b>Flag FPY :</b> {test.FPY_flag}<br>
            </div>
            <hr>
            """
        )

    return HttpResponse("".join(lignes))