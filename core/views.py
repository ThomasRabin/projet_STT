from django.http import HttpResponse
from django.utils import timezone

from .models import OF, LogTest, Produit, ReferenceProduit, PassageTest
from django.utils.html import escape

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
    Affiche les logs présents en base.
    Filtre optionnel par numéro de série produit via ?sn=...
    Exemple :
        /core/logs/?sn=1234567000005
    """

    sn = request.GET.get("sn", "").strip()

    logs = (
        LogTest.objects
        .select_related("idTest", "idTest__idProduit")
        .all()
        .order_by("-dateEtape")
    )

    if sn:
        logs = logs.filter(idTest__idProduit__SN=sn)

    lignes = []

    lignes.append(
        f"""
        <form method="get" style="margin-bottom:20px;">
            <label for="sn"><b>Filtrer par SN :</b></label>
            <input type="text" id="sn" name="sn" value="{escape(sn)}">
            <button type="submit">Filtrer</button>
            <a href="{request.path}">Réinitialiser</a>
        </form>
        <hr>
        """
    )

    if not logs.exists():
        lignes.append(
            f"""
            <p>Aucun log trouvé{f" pour le SN {escape(sn)}" if sn else ""}.</p>
            """
        )

    for log in logs:
        if log.dateEtape:
            date_locale = timezone.localtime(log.dateEtape)
            date_formattee = date_locale.strftime("%d/%m/%Y %H:%M:%S")
        else:
            date_formattee = "N/A"

        lignes.append(
            f"""
            <div style="margin-bottom:15px;">
                <b>Rapport :</b> {escape(log.idTest.idRapport or "")}<br>
                <b>SN :</b> {escape(log.idTest.idProduit.SN or "")}<br>
                <b>Étape :</b> {escape(str(log.numeroEtape))} - {escape(log.nomEtape or "")}<br>
                <b>Résultat :</b> {log.resultatEtape}<br>
                <b>Composant :</b> {escape(log.composant or "")}<br>
                <b>Référence composant :</b> {escape(log.refComposant or "")}<br>
                <b>Face :</b> {escape(log.face or "")}<br>
                <b>Position :</b> {log.position}<br>
                <b>Date :</b> {date_formattee}
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
                <b>Machine :</b> {test.idOperation.idMachine}<br>
                <b>Interface :</b> {test.idInterfaceUtilisee}<br>
                <b>Version logiciel :</b> {test.versionLogiciel}<br>
                <b>Opérateur :</b> {test.codeOperateur}<br>
            </div>
            <hr>
            """
        )

    return HttpResponse("".join(lignes))