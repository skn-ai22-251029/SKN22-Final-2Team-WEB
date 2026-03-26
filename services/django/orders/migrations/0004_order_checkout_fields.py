from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0003_wishlist_wishlistitem"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="applied_coupon_id",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="order",
            name="coupon_discount",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="order",
            name="delivery_message",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="order",
            name="mileage_discount",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="order",
            name="payment_method",
            field=models.CharField(default="", max_length=120),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="order",
            name="product_total",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="order",
            name="recipient_phone",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="order",
            name="shipping_fee",
            field=models.IntegerField(default=0),
        ),
    ]
