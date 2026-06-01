from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_remove_carte_statut_carte"),
    ]

    operations = [
        migrations.AlterField(
            model_name="compositionpanel",
            name="idCarte",
            field=models.ForeignKey(
                to="core.carte",
                on_delete=django.db.models.deletion.CASCADE,
                blank=True,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="compositionpanel",
            name="statutCarte",
            field=models.CharField(
                max_length=30,
                choices=[
                    ("OK", "OK"),
                    ("A_ANALYSER", "A analyser"),
                    ("A_REPARER", "A réparer"),
                    ("A_RETESTER", "A retester"),
                    ("REBUT", "Rebut"),
                ],
                default="OK",
            ),
            preserve_default=False,
        ),
    ]
