from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0004_order_checkout_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "주문 접수"),
                    ("shipping", "배송 중"),
                    ("completed", "배송 완료"),
                    ("cancelled", "주문 취소"),
                ],
                default="pending",
                max_length=15,
            ),
        ),
    ]
