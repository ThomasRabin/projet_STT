from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("ofs/", views.of_list, name="of_list"),
    path("references/", views.reference_list, name="reference_list"),
    path("produits/", views.produit_list, name="produit_list"),
]