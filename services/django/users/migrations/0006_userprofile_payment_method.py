from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0005_local_db_schema_alignment"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="payment_method",
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
    ]
