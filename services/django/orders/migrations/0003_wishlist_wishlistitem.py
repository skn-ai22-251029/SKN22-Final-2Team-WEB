import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0002_initial"),
        ("products", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Wishlist",
            fields=[
                ("wishlist_id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "wishlist",
            },
        ),
        migrations.CreateModel(
            name="WishlistItem",
            fields=[
                ("wishlist_item_id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("added_at", models.DateTimeField(auto_now_add=True)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name="wishlist_items", to="products.product")),
                ("wishlist", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="orders.wishlist")),
            ],
            options={
                "db_table": "wishlist_item",
                "unique_together": {("wishlist", "product")},
            },
        ),
    ]
