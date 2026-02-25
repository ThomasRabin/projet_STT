from django.http import HttpResponse
from .models import OF, Produit, ReferenceProduit

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