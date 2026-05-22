"""
@file serializers.py
@brief Serializers DRF pour la validation structurelle des rapports JSON.

@details
Ce module décrit la structure attendue des rapports entrants :
- produit principal
- panel optionnel
- cartes du panel optionnelles individuellement en SN
- informations OF / opération / machine / test
- défaut optionnel
- logs de test

La validation métier approfondie reste dans AuditeurRapport.
"""

from rest_framework import serializers


STATUT_PRODUIT_VALUES = [
    "OK",
    "A_ANALYSER",
    "A_REPARER",
    "A_RETESTER",
    "REBUT",
]


class CartePanelSerializer(serializers.Serializer):
    position = serializers.IntegerField(min_value=1)
    snCarte = serializers.CharField(max_length=30, required=False, allow_null=True)
    statutCarte = serializers.ChoiceField(choices=STATUT_PRODUIT_VALUES)


class PanelSerializer(serializers.Serializer):
    nombreCartes = serializers.IntegerField(min_value=1)
    cartes = CartePanelSerializer(many=True)

    def validate(self, data):
        nombre_cartes = data["nombreCartes"]
        cartes = data["cartes"]

        if len(cartes) != nombre_cartes:
            raise serializers.ValidationError(
                {"cartes": "Le nombre d'éléments de cartes doit être égal à nombreCartes"}
            )

        positions = [c["position"] for c in cartes]
        if len(set(positions)) != len(positions):
            raise serializers.ValidationError(
                {"cartes": "Les positions des cartes doivent être uniques"}
            )

        return data


class ProduitSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["CARTE", "PANEL"])
    sn = serializers.CharField(max_length=30, required=False, allow_null=True)
    pn = serializers.CharField(max_length=30, required=False, allow_null=True)
    statutProduit = serializers.ChoiceField(choices=STATUT_PRODUIT_VALUES)


class OFSerializer(serializers.Serializer):
    numeroOF = serializers.RegexField(r"^\d{7}$")
    client = serializers.CharField(max_length=30, required=False, allow_null=True)


class OperationSerializer(serializers.Serializer):
    typeOperation = serializers.ChoiceField(
        choices=["AUTOMATIQUE", "MANUELLE", "TEST", "CONTROLE"]
    )
    numeroOperation = serializers.IntegerField(
        required=False, allow_null=True, min_value=0
    )
    nomOperation = serializers.CharField(max_length=30)
    dateFinOperation = serializers.DateTimeField(required=False, allow_null=True)


class MachineSerializer(serializers.Serializer):
    codeMachine = serializers.CharField(max_length=30)
    typeMachine = serializers.ChoiceField(
        choices=["CMS", "VAGUE", "AOI", "ICT", "FCT", "PROGRAMMATION", "VRT", "AUTRE"]
    )
    interface = serializers.CharField(max_length=10, required=False, allow_null=True)


class LogSerializer(serializers.Serializer):
    dateEtape = serializers.DateTimeField(required=False, allow_null=True)
    face = serializers.ChoiceField(
        choices=["TOP", "BOTTOM"], required=False, allow_null=True
    )
    position = serializers.IntegerField(min_value=1)
    numeroEtape = serializers.IntegerField(required=False, allow_null=True)
    nomEtape = serializers.CharField(max_length=150)
    messageErreur = serializers.CharField(required=False, allow_null=True)
    limMoins = serializers.FloatField(required=False, allow_null=True)
    limPlus = serializers.FloatField(required=False, allow_null=True)
    valeurMesuree = serializers.FloatField(required=False, allow_null=True)
    unite = serializers.CharField(max_length=20, required=False, allow_null=True)
    resultatEtape = serializers.BooleanField()
    composant = serializers.CharField(max_length=10, required=False, allow_null=True)
    refComposant = serializers.CharField(max_length=30, required=False, allow_null=True)


class DefautSerializer(serializers.Serializer):
    numeroDefaut = serializers.IntegerField(required=False, allow_null=True)
    nomDefaut = serializers.CharField(max_length=150)
    dateDefaut = serializers.DateTimeField()
    dateRework = serializers.DateTimeField(required=False, allow_null=True)
    commentaireDefaut = serializers.CharField(required=False, allow_null=True)


class TestSerializer(serializers.Serializer):
    face = serializers.ChoiceField(
        choices=["TOP", "BOTTOM"], required=False, allow_null=True
    )
    etatTest = serializers.BooleanField()
    resultatTest = serializers.CharField(max_length=150)
    dateFinTest = serializers.DateTimeField()
    versionLogiciel = serializers.CharField(
        max_length=100, required=False, allow_null=True
    )
    codeOperateur = serializers.CharField(max_length=50, required=False, allow_null=True)


class RapportEntreeSerializer(serializers.Serializer):
    idRapport = serializers.RegexField(r"^RPT-[A-Za-z0-9_]+-\d{14}$")
    createdAt = serializers.DateTimeField(required=False, allow_null=True)

    produit = ProduitSerializer()
    panel = PanelSerializer(required=False, allow_null=True)

    of = OFSerializer()
    operation = OperationSerializer()
    machine = MachineSerializer()
    test = TestSerializer()
    logs = LogSerializer(many=True, allow_empty=True)
    defaut = DefautSerializer(required=False, allow_null=True)