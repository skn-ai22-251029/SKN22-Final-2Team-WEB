from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0007_userprofile_phone_verification_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="recipient_name",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="postal_code",
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="address_main",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="address_detail",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="payment_card_provider",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="payment_card_masked_number",
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="payment_is_default",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="payment_token_reference",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
