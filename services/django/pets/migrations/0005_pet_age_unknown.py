from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pets", "0004_alter_pet_gender"),
    ]

    operations = [
        migrations.AddField(
            model_name="pet",
            name="age_unknown",
            field=models.BooleanField(default=False),
        ),
    ]
