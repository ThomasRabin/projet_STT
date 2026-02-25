from django.db import models
from django.core.validators import (
    MinLengthValidator,
    MaxLengthValidator,
    MinValueValidator,
    MaxValueValidator,
)

########################## Enumérations ##########################
STATUT_PRODUIT_CHOICES = [
    ("OK", "OK"),
    ("A_ANALYSER", "A_ANALYSER"),
    ("A_REPARER", "A_REPARER"),
    ("A_RETESTER", "A_RETESTER"),
    ("REBUTER", "REBUTER"),
]

STATUT_OF_CHOICES = [
    ("CREE", "CREE"),
    ("EN_COURS", "EN_COURS"),
    ("TERMINE", "TERMINE"),
    ("INCOMPLET", "INCOMPLET"),
    ("BLOQUE", "BLOQUE"),
]

TYPE_MACHINE_CHOICES = [
    ("CMS", "CMS"),
    ("VAGUE", "VAGUE"),
    ("AOI", "AOI"),
    ("ICT", "ICT"),
    ("FCT", "FCT"),
    ("PROGRAMMATION", "PROGRAMMATION"),
    ("VRT", "VRT"),
    ("AUTRE", "AUTRE"),
]

TYPE_OPERATION_CHOICES = [
    ("AUTOMATIQUE", "AUTOMATIQUE"),
    ("MANUELLE", "MANUELLE"),
    ("TEST", "TEST"),
    ("CONTROLE", "CONTROLE"),
]

########################### Modèles ##########################
class ReferenceProduit(models.Model):
    PN = models.CharField(max_length=30, unique=True)
    description = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self) -> str:
        return self.PN


class OF(models.Model):
    idReferenceProduit = models.ForeignKey(ReferenceProduit, on_delete=models.PROTECT)

    # Un numéro d'OF est généralement un code (zéros possibles) => CharField conseillé
    numeroOF = models.CharField(
        max_length=7,
        validators=[MinLengthValidator(7), MaxLengthValidator(7)],
        unique=True,
    )

    client = models.CharField(max_length=30)
    dateLancement = models.DateField(blank=True, null=True)  # Non applicable en v1
    statutOF = models.CharField(
        max_length=30, choices=STATUT_OF_CHOICES, blank=True, null=True
    )  # Non applicable en v1
    quantite = models.IntegerField(validators=[MinValueValidator(0)])

    def __str__(self) -> str:
        return f"OF-{self.numeroOF}"


class Produit(models.Model):
    idReferenceProduit = models.ForeignKey(ReferenceProduit, on_delete=models.PROTECT)
    SN = models.CharField(max_length=30, unique=True)
    statutProduit = models.CharField(max_length=30, choices=STATUT_PRODUIT_CHOICES)

    def __str__(self) -> str:
        return f"{self.idReferenceProduit.PN} - {self.SN}"


class AffectationProduitOF(models.Model):
    idProduit = models.ForeignKey(
        Produit, on_delete=models.CASCADE, related_name="affectations"
    )
    idOF = models.ForeignKey(OF, on_delete=models.CASCADE, related_name="affectations")
    dateAffectation = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["idProduit", "dateAffectation"]),
            models.Index(fields=["idOF", "dateAffectation"]),
        ]
        constraints = [
            # Empêche les doublons stricts (même produit, même OF, même timestamp)
            models.UniqueConstraint(
                fields=["idProduit", "idOF", "dateAffectation"],
                name="uniq_affectation_produit_of_date",
            )
        ]


# Héritage de Produit pour Carte et Panel (multi-table inheritance)
class Carte(Produit):
    statutCarte = models.CharField(max_length=30, choices=STATUT_PRODUIT_CHOICES)


class Panel(Produit):
    nombreCartes = models.IntegerField(validators=[MinValueValidator(0)])


class CompositionPanel(models.Model):
    idPanel = models.ForeignKey(Panel, on_delete=models.CASCADE)
    idCarte = models.ForeignKey(Carte, on_delete=models.CASCADE)
    position = models.IntegerField(validators=[MinValueValidator(1)])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["idPanel", "position"], name="unique_panel_position"
            ),
            models.UniqueConstraint(
                fields=["idPanel", "idCarte"], name="unique_panel_carte"
            ),
        ]

class InterfaceMachine(models.Model):
    codeInterface = models.CharField(max_length=10, unique=True)
    nomInterface = models.CharField(max_length=30)
    anneeInterface = models.IntegerField(
        validators=[MinValueValidator(1900), MaxValueValidator(2200)]
    )
    nbPassageInterface = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    dateDerniereMaintenanceInterface = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.codeInterface

class Machine(models.Model):
    codeMachine = models.CharField(max_length=10, unique=True)
    nomMachine = models.CharField(max_length=30)
    typeMachine = models.CharField(max_length=30, choices=TYPE_MACHINE_CHOICES)
    anneeMachine = models.IntegerField(
        validators=[MinValueValidator(1900), MaxValueValidator(2200)]
    )
    dateDerniereMaintenanceMachine = models.DateField()
    nbPassageMachine = models.IntegerField(validators=[MinValueValidator(0)], default=0)

    interfaces = models.ManyToManyField(InterfaceMachine, blank=True, related_name="machines")

    def __str__(self):
        return self.codeMachine


class Operation(models.Model):
    idOF = models.ForeignKey(OF, on_delete=models.CASCADE)
    idMachine = models.ForeignKey(
        Machine, on_delete=models.SET_NULL, blank=True, null=True
    )
    numeroOperation = models.IntegerField(blank=True, null=True)  # Non applicable en v1
    nomOperation = models.CharField(max_length=30)
    typeOperation = models.CharField(max_length=30, choices=TYPE_OPERATION_CHOICES)
    dateFinOperation = models.DateTimeField(blank=True, null=True)

FACE_CHOICES = [
    ("TOP", "TOP"),
    ("BOTTOM", "BOTTOM"),
]

class Test(models.Model):
    idProduit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    idOperation = models.ForeignKey(
        Operation, on_delete=models.SET_NULL, blank=True, null=True
    )
    face = models.CharField(max_length=6, choices=FACE_CHOICES, blank=True, null=True)
    etatTest = models.BooleanField()
    resultatTest = models.CharField(max_length=50)
    codeOperateur = models.IntegerField(blank=True, null=True)  # Non applicable en v1
    FPY_flag = models.BooleanField()
    dateFinTest = models.DateTimeField()
    versionLogiciel = models.CharField(max_length=30, blank=True, null=True)


class LogTest(models.Model):
    idTest = models.ForeignKey(Test, on_delete=models.CASCADE)
    dateEtape = models.DateTimeField(blank=True, null=True)
    numeroEtape = models.IntegerField(blank=True, null=True)
    nomEtape = models.CharField(max_length=50)
    limPlus = models.FloatField(blank=True, null=True)
    limMoins = models.FloatField(blank=True, null=True)
    valeurMesuree = models.FloatField(blank=True, null=True)
    unite = models.CharField(max_length=20, blank=True, null=True)
    resultatEtape = models.BooleanField()
    composant = models.CharField(max_length=10, blank=True, null=True)
    refComposant = models.CharField(max_length=30, blank=True, null=True)
    face = models.CharField(max_length=30, blank=True, null=True)
    imageTest = models.ImageField(upload_to="images/", blank=True, null=True)


class Defaut(models.Model):
    idTest = models.OneToOneField(Test, on_delete=models.CASCADE)
    numeroDefaut = models.IntegerField(blank=True, null=True)
    nomDefaut = models.CharField(max_length=50)
    dateDefaut = models.DateTimeField()
    dateRework = models.DateTimeField(blank=True, null=True)  # Non applicable en v1
    commentaireDefaut = models.TextField(blank=True, null=True)