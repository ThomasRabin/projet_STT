from django.urls import path
from . import views
from .ingestion.receptionneur import recevoir_rapport

urlpatterns = [
    path("", views.index, name="index"),
    path("ofs/", views.of_list, name="of_list"),
    path("references/", views.reference_list, name="reference_list"),
    path("produits/", views.produit_list, name="produit_list"),
    path("ingestion/rapport/", recevoir_rapport, name="recevoir_rapport"),
]