from django.contrib import admin

from .models import (
    ReferenceProduit, OF, Produit, AffectationProduitOF, Carte, Panel,
    CompositionPanel, Machine, InterfaceMachine, Operation, Test,
    LogTest, Defaut
)

# Register your models here.
admin.site.register(ReferenceProduit)
admin.site.register(OF)
admin.site.register(Produit)
admin.site.register(AffectationProduitOF)
admin.site.register(Carte)
admin.site.register(Panel)
admin.site.register(CompositionPanel)
admin.site.register(Machine)
admin.site.register(InterfaceMachine)
admin.site.register(Operation)
admin.site.register(Test)
admin.site.register(LogTest)
admin.site.register(Defaut)