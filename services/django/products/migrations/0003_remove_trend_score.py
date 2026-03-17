from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0002_add_category_fields"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="product",
            name="product_trend_s_47c0b1_idx",
        ),
        migrations.RemoveField(
            model_name="product",
            name="trend_score",
        ),
    ]
