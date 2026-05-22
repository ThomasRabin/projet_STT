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
    ("A_ANALYSER", "A analyser"),
    ("A_REPARER", "A réparer"),
    ("A_RETESTER", "A retester"),
    ("REBUT", "Rebut"),
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

FACE_CHOICES = [
    ("TOP", "TOP"),
    ("BOTTOM", "BOTTOM"),
]

########################### Modèles ##########################
class ReferenceProduit(models.Model):
    PN = models.CharField(max_length=30, unique=True)
    description = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self) -> str:
        return self.PN


class OF(models.Model):
    idReferenceProduit = models.ForeignKey(ReferenceProduit, on_delete=models.PROTECT)

    numeroOF = models.CharField(
        max_length=7,
        validators=[MinLengthValidator(7), MaxLengthValidator(7)],
        unique=True,
    )

    client = models.CharField(max_length=30, blank=True, null=True)
    dateLancement = models.DateField(blank=True, null=True)
    statutOF = models.CharField(
        max_length=30, choices=STATUT_OF_CHOICES, blank=True, null=True
    )
    quantite = models.IntegerField(validators=[MinValueValidator(0)], default=0)

    def __str__(self) -> str:
        return f"OF-{self.numeroOF}"


class Produit(models.Model):
    """
    @brief Produit tracé dans le système.

    @details
    Tout objet identifié par un SN est un produit.
    Le SN peut être nul dans le cas d'un panel sans snPanel remonté par l'ETL.
    """
    idReferenceProduit = models.ForeignKey(
        ReferenceProduit, on_delete=models.PROTECT, blank=True, null=True
    )
    SN = models.CharField(max_length=30, unique=True, blank=True, null=True)
    statutProduit = models.CharField(max_length=30, choices=STATUT_PRODUIT_CHOICES)

    def __str__(self) -> str:
        return f"{self.idReferenceProduit_id} - {self.SN}"


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
            models.UniqueConstraint(
                fields=["idProduit", "idOF", "dateAffectation"],
                name="uniq_affectation_produit_of_date",
            )
        ]


class Carte(Produit):
    """
    @brief Spécialisation d'un produit de type carte.
    """
    pass


class Panel(Produit):
    """
    @brief Spécialisation d'un produit de type panel.
    """
    nombreCartes = models.IntegerField(validators=[MinValueValidator(0)])


class CompositionPanel(models.Model):
    """
    @brief Composition physique d'un panel.

    @details
    Une position de panel peut référencer :
    - une carte identifiée (idCarte non null)
    - ou seulement une position + statut si la carte n'a pas de SN
    """
    idPanel = models.ForeignKey(Panel, on_delete=models.CASCADE, related_name="compositions")
    idCarte = models.ForeignKey(Carte, on_delete=models.CASCADE, blank=True, null=True)
    position = models.IntegerField(validators=[MinValueValidator(1)])
    statutCarte = models.CharField(max_length=30, choices=STATUT_PRODUIT_CHOICES)

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
    nbPassageInterface = models.IntegerField(
        validators=[MinValueValidator(0)], default=0
    )
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
    nbPassageMachine = models.IntegerField(
        validators=[MinValueValidator(0)], default=0
    )

    interfaces = models.ManyToManyField(
        InterfaceMachine, blank=True, related_name="machines"
    )

    def __str__(self):
        return self.codeMachine


class Operation(models.Model):
    idOF = models.ForeignKey(OF, on_delete=models.CASCADE)
    idMachine = models.ForeignKey(
        Machine, on_delete=models.SET_NULL, blank=True, null=True
    )
    numeroOperation = models.IntegerField(blank=True, null=True)
    nomOperation = models.CharField(max_length=30)
    typeOperation = models.CharField(max_length=30, choices=TYPE_OPERATION_CHOICES)
    dateFinOperation = models.DateTimeField(blank=True, null=True)


class PassageTest(models.Model):
    idProduit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    idOperation = models.ForeignKey(
        Operation, on_delete=models.SET_NULL, blank=True, null=True
    )
    idInterfaceUtilisee = models.ForeignKey(
        InterfaceMachine,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="tests",
    )
    idRapport = models.CharField(max_length=50, unique=True, null=True, blank=True)
    face = models.CharField(max_length=6, choices=FACE_CHOICES, blank=True, null=True)
    etatTest = models.BooleanField()
    resultatTest = models.CharField(max_length=150)
    codeOperateur = models.CharField(max_length=50, blank=True, null=True)
    FPY_flag = models.BooleanField()
    dateFinTest = models.DateTimeField()
    versionLogiciel = models.CharField(max_length=100, blank=True, null=True)


class LogTest(models.Model):
    idTest = models.ForeignKey(PassageTest, on_delete=models.CASCADE)
    dateEtape = models.DateTimeField(blank=True, null=True)
    face = models.CharField(max_length=6, choices=FACE_CHOICES, blank=True, null=True)
    position = models.IntegerField(validators=[MinValueValidator(1)], default=1)
    numeroEtape = models.IntegerField(blank=True, null=True)
    nomEtape = models.CharField(max_length=150)
    messageErreur = models.CharField(max_length=255, blank=True, null=True)
    limPlus = models.FloatField(blank=True, null=True)
    limMoins = models.FloatField(blank=True, null=True)
    valeurMesuree = models.FloatField(blank=True, null=True)
    unite = models.CharField(max_length=20, blank=True, null=True)
    resultatEtape = models.BooleanField()
    composant = models.CharField(max_length=10, blank=True, null=True)
    refComposant = models.CharField(max_length=30, blank=True, null=True)


class Defaut(models.Model):
    idTest = models.OneToOneField(PassageTest, on_delete=models.CASCADE)
    numeroDefaut = models.IntegerField(blank=True, null=True)
    nomDefaut = models.CharField(max_length=150)
    dateDefaut = models.DateTimeField()
    dateRework = models.DateTimeField(blank=True, null=True)
    commentaireDefaut = models.TextField(blank=True, null=True)