from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pets", "0003_future_pet_profile_and_food_choices"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pet",
            name="gender",
            field=models.CharField(blank=True, choices=[("male", "수컷"), ("female", "암컷")], default="", max_length=10),
        ),
    ]
