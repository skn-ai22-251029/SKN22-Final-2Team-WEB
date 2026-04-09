from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0005_alter_order_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userinteraction",
            name="interaction_type",
            field=models.CharField(
                choices=[
                    ("impression", "노출"),
                    ("click", "클릭"),
                    ("detail_view", "상세 진입"),
                    ("wishlist", "관심 상품"),
                    ("cart", "장바구니"),
                    ("checkout_start", "체크아웃 시작"),
                    ("purchase", "구매"),
                    ("reject", "거절"),
                ],
                max_length=20,
            ),
        ),
    ]
