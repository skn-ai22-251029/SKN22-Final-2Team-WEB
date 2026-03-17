import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="soldout_reliable",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="product",
            name="pet_type",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=20),
                default=list,
                size=None,
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="category",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=50),
                default=list,
                size=None,
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="subcategory",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=100),
                default=list,
                size=None,
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="health_concern_tags",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=20),
                default=list,
                size=None,
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="sentiment_avg",
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True),
        ),
        migrations.AddField(
            model_name="product",
            name="repeat_rate",
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["pet_type"], name="product_pet_type_idx"),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["category"], name="product_category_idx"),
        ),
    ]
