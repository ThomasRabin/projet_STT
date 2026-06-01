# Generated manually to remove obsolete Carte.statutCarte field.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_passagetest_idinterfaceutilisee_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="carte",
            name="statutCarte",
        ),
    ]
