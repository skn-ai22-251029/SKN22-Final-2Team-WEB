import uuid
from django.contrib.postgres.fields import ArrayField
from django.db import models


class Product(models.Model):
    goods_id               = models.CharField(max_length=20, primary_key=True)
    goods_name             = models.TextField()
    brand_name             = models.CharField(max_length=200)
    price                  = models.IntegerField()
    discount_price         = models.IntegerField()
    rating                 = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    review_count           = models.IntegerField(default=0)
    thumbnail_url          = models.TextField()
    product_url            = models.TextField()
    soldout_yn             = models.BooleanField(default=False)
    soldout_reliable       = models.BooleanField(default=True)
    pet_type               = ArrayField(models.CharField(max_length=20), default=list)
    category               = ArrayField(models.CharField(max_length=50), default=list)
    subcategory            = ArrayField(models.CharField(max_length=100), default=list)
    health_concern_tags    = ArrayField(models.CharField(max_length=20), default=list)
    popularity_score       = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    sentiment_avg          = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    repeat_rate            = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    main_ingredients       = models.JSONField(null=True, blank=True)
    ingredient_composition = models.JSONField(null=True, blank=True)
    nutrition_info         = models.JSONField(null=True, blank=True)
    ingredient_text_ocr    = models.TextField(null=True, blank=True)
    crawled_at             = models.DateTimeField()

    class Meta:
        db_table = "product"
        indexes = [
            models.Index(fields=["brand_name"]),
            models.Index(fields=["-popularity_score"]),
        ]


class ProductCategoryTag(models.Model):
    TAG_CHOICES = [
        ("관절", "관절"), ("피부", "피부"), ("소화", "소화"), ("체중", "체중"),
        ("요로", "요로"), ("눈물", "눈물"), ("헤어볼", "헤어볼"), ("치아", "치아"), ("면역", "면역"),
    ]
    id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="category_tags")
    tag     = models.CharField(max_length=20, choices=TAG_CHOICES)

    class Meta:
        db_table = "product_category_tag"
        unique_together = [("product", "tag")]


class Review(models.Model):
    review_id       = models.CharField(max_length=30, primary_key=True)
    product         = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    score           = models.DecimalField(max_digits=2, decimal_places=1)
    content         = models.TextField()
    author_nickname = models.CharField(max_length=100)
    written_at      = models.DateField()
    purchase_label  = models.CharField(
        max_length=10, null=True, blank=True,
        choices=[("first", "첫 구매"), ("repeat", "재구매")]
    )
    sentiment_score = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    sentiment_label = models.CharField(
        max_length=10, null=True, blank=True,
        choices=[("positive", "긍정"), ("negative", "부정"), ("neutral", "중립")]
    )
    absa_result    = models.JSONField(null=True, blank=True)
    pet_age_months = models.IntegerField(null=True, blank=True)
    pet_weight_kg  = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    pet_gender     = models.CharField(max_length=10, null=True, blank=True)
    pet_breed      = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = "review"
        indexes = [
            models.Index(fields=["product"]),
            models.Index(fields=["-written_at"]),
        ]


class ProductAdminConfig(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product      = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="admin_config")
    admin_weight = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    pinned       = models.BooleanField(default=False)
    memo         = models.TextField(null=True, blank=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product_admin_config"
