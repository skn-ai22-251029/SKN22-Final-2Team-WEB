from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0006_userprofile_payment_method"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="phone_verified",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="phone_verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="phone_verification_code",
            field=models.CharField(blank=True, max_length=6, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="phone_verification_target",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="phone_verification_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
