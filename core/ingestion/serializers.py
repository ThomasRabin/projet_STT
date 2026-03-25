from rest_framework import serializers


STATUT_PRODUIT_VALUES = [
    "OK",
    "A analyser",
    "A réparer",
    "A retester",
    "Rebut",
]


class ProduitCarteSerializer(serializers.Serializer):
    statutCarte = serializers.ChoiceField(choices=STATUT_PRODUIT_VALUES)


class ProduitPanelSerializer(serializers.Serializer):
    nombreCartes = serializers.IntegerField(min_value=1)


class ProduitSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["CARTE", "PANEL"])
    sn = serializers.CharField(max_length=30)
    pn = serializers.CharField(max_length=30)
    statutProduit = serializers.ChoiceField(choices=STATUT_PRODUIT_VALUES)
    carte = ProduitCarteSerializer(required=False, allow_null=True)
    panel = ProduitPanelSerializer(required=False, allow_null=True)

    def validate(self, data):
        type_produit = data["type"]
        carte = data.get("carte")
        panel = data.get("panel")

        if type_produit == "CARTE":
            if carte is None:
                raise serializers.ValidationError(
                    {"carte": "obligatoire quand produit.type = CARTE"}
                )
            if panel is not None:
                raise serializers.ValidationError(
                    {"panel": "doit être absent ou null quand produit.type = CARTE"}
                )

        if type_produit == "PANEL":
            if panel is None:
                raise serializers.ValidationError(
                    {"panel": "obligatoire quand produit.type = PANEL"}
                )
            if carte is not None:
                raise serializers.ValidationError(
                    {"carte": "doit être absent ou null quand produit.type = PANEL"}
                )

        return data


class OFSerializer(serializers.Serializer):
    numeroOF = serializers.RegexField(r"^\d{7}$")
    client = serializers.CharField(max_length=30)
    quantite = serializers.IntegerField(min_value=0)


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
    interface = serializers.CharField(max_length=10)


class LogSerializer(serializers.Serializer):
    dateEtape = serializers.DateTimeField(required=False, allow_null=True)
    face = serializers.ChoiceField(
        choices=["TOP", "BOTTOM"], required=False, allow_null=True
    )
    position = serializers.IntegerField(min_value=1)

    numeroEtape = serializers.IntegerField(required=False, allow_null=True)
    nomEtape = serializers.CharField(max_length=50)
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
    nomDefaut = serializers.CharField(max_length=50)
    dateDefaut = serializers.DateTimeField()
    dateRework = serializers.DateTimeField(required=False, allow_null=True)
    commentaireDefaut = serializers.CharField(required=False, allow_null=True)


class TestSerializer(serializers.Serializer):
    face = serializers.ChoiceField(
        choices=["TOP", "BOTTOM"], required=False, allow_null=True
    )
    etatTest = serializers.BooleanField()
    resultatTest = serializers.CharField(max_length=50)
    dateFinTest = serializers.DateTimeField()
    versionLogiciel = serializers.CharField(
        max_length=30, required=False, allow_null=True
    )
    codeOperateur = serializers.IntegerField(required=False, allow_null=True)


class RapportEntreeSerializer(serializers.Serializer):
    idRapport = serializers.RegexField(
        r"^RPT-[A-Za-z0-9_]+-\d{14}$"
    )
    createdAt = serializers.DateTimeField(required=False, allow_null=True)

    produit = ProduitSerializer()
    of = OFSerializer()
    operation = OperationSerializer()
    machine = MachineSerializer()
    test = TestSerializer()
    logs = LogSerializer(many=True, allow_empty=False)
    defaut = DefautSerializer(required=False, allow_null=True)