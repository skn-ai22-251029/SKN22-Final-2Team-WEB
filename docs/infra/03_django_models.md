# Django Models 가이드

> 실제 DDL은 Django 마이그레이션으로 관리. `models.py`가 단일 진실 공급원.

---

## 1. 앱별 모델 분리 기준

| Django 앱 | 모델 | 비고 |
|-----------|------|------|
| `users` | User, UserProfile | AbstractBaseUser 확장. 이메일 기반 인증 |
| `pets` | Pet, PetHealthConcern, PetAllergy, PetFoodPreference, PetUsedProduct | |
| `products` | Product, ProductCategoryTag, Review, ProductAdminConfig | Product/Review는 파이프라인 INSERT · Django READ 전용 |
| `orders` | Cart, CartItem, Order, OrderItem, UserInteraction | |
| `chat` | ChatSession, ChatMessage, MessageProductCard | FastAPI와 공유 테이블 |

---

## 2. models.py

### users/models.py

```python
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("이메일은 필수입니다.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id         = models.AutoField(primary_key=True)
    email      = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active  = models.BooleanField(default=True)
    is_staff   = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "user"


class UserProfile(models.Model):
    user              = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name="profile")
    nickname          = models.CharField(max_length=100)
    age               = models.IntegerField(null=True, blank=True)
    gender            = models.CharField(max_length=20, null=True, blank=True)
    address           = models.TextField(null=True, blank=True)
    phone             = models.CharField(max_length=20, null=True, blank=True)
    marketing_consent = models.BooleanField(default=False)
    profile_image_url = models.TextField(null=True, blank=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_profile"
```

---

### pets/models.py

```python
import uuid
from django.db import models
from products.models import Product
from users.models import User


class Pet(models.Model):
    SPECIES_CHOICES = [("cat", "고양이"), ("dog", "강아지")]
    GENDER_CHOICES  = [("male", "수컷"), ("female", "암컷")]

    pet_id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user             = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pets")
    name             = models.CharField(max_length=100)
    species          = models.CharField(max_length=5, choices=SPECIES_CHOICES)
    breed            = models.CharField(max_length=100, null=True, blank=True)
    gender           = models.CharField(max_length=10, choices=GENDER_CHOICES)
    age_years        = models.IntegerField(default=0)
    age_months       = models.IntegerField(default=0)
    weight_kg        = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    neutered         = models.BooleanField(null=True, blank=True)
    vaccination_date = models.DateField(null=True, blank=True)
    budget_range     = models.CharField(max_length=20)
    special_notes    = models.TextField(null=True, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pet"


class PetHealthConcern(models.Model):
    CONCERN_CHOICES = [
        ("skin", "피부"), ("joint", "관절"), ("digestion", "소화"), ("weight", "체중"),
        ("urinary", "요로"), ("eye", "눈물"), ("hairball", "헤어볼"), ("dental", "치아"), ("immunity", "면역"),
    ]
    id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pet     = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="health_concerns")
    concern = models.CharField(max_length=20, choices=CONCERN_CHOICES)

    class Meta:
        db_table      = "pet_health_concern"
        unique_together = [("pet", "concern")]


class PetAllergy(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pet        = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="allergies")
    ingredient = models.CharField(max_length=100)

    class Meta:
        db_table      = "pet_allergy"
        unique_together = [("pet", "ingredient")]


class PetFoodPreference(models.Model):
    FOOD_TYPE_CHOICES = [
        ("dry", "건식"), ("wet_can", "습식캔"), ("wet_pouch", "습식파우치"),
        ("freeze_dried", "동결건조"), ("raw", "생식"),
    ]
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pet       = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="food_preferences")
    food_type = models.CharField(max_length=20, choices=FOOD_TYPE_CHOICES)

    class Meta:
        db_table      = "pet_food_preference"
        unique_together = [("pet", "food_type")]


class PetUsedProduct(models.Model):
    id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pet     = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="used_products")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="used_by_pets")

    class Meta:
        db_table      = "pet_used_product"
        unique_together = [("pet", "product")]
```

---

### products/models.py

```python
import uuid
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from pgvector.django import VectorField


class Product(models.Model):
    goods_id               = models.CharField(max_length=20, primary_key=True)
    prefix                 = models.CharField(max_length=5)  # GI/GP/GO/GS/PI
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
    embedding              = VectorField(dimensions=1024, null=True, blank=True)  # pgvector Dense
    embedding_text         = models.TextField(null=True, blank=True)              # 임베딩 원본 텍스트
    search_vector          = SearchVectorField(null=True)                         # Kiwi tsvector
    crawled_at             = models.DateTimeField()

    class Meta:
        db_table = "product"
        indexes  = [
            models.Index(fields=["brand_name"]),
            models.Index(fields=["-popularity_score"]),
            models.Index(fields=["prefix"]),
        ]
    # HNSW(embedding), GIN(search_vector) 인덱스는 마이그레이션에서 RunSQL로 생성


class ProductCategoryTag(models.Model):
    TAG_CHOICES = [
        ("관절", "관절"), ("피부", "피부"), ("소화", "소화"), ("체중", "체중"),
        ("요로", "요로"), ("눈물", "눈물"), ("헤어볼", "헤어볼"), ("치아", "치아"), ("면역", "면역"),
    ]
    id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="category_tags")
    tag     = models.CharField(max_length=20, choices=TAG_CHOICES)

    class Meta:
        db_table      = "product_category_tag"
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
        indexes  = [
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
```

---

### orders/models.py

```python
import uuid
from django.db import models
from users.models import User
from products.models import Product


class Cart(models.Model):
    cart_id    = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.OneToOneField(User, on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cart"


class CartItem(models.Model):
    cart_item_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart         = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product      = models.ForeignKey(Product, on_delete=models.RESTRICT, related_name="cart_items")
    quantity     = models.IntegerField(default=1)
    added_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table      = "cart_item"
        unique_together = [("cart", "product")]


class Order(models.Model):
    STATUS_CHOICES = [("pending", "주문 접수"), ("completed", "배송 완료"), ("cancelled", "취소")]

    order_id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user             = models.ForeignKey(User, on_delete=models.RESTRICT, related_name="orders")
    recipient_name   = models.CharField(max_length=100)
    delivery_address = models.TextField()
    total_price      = models.IntegerField()
    status           = models.CharField(max_length=15, default="pending", choices=STATUS_CHOICES)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "order"


class OrderItem(models.Model):
    order_item_id  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order          = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product        = models.ForeignKey(Product, on_delete=models.RESTRICT, related_name="order_items")
    quantity       = models.IntegerField()
    price_at_order = models.IntegerField()

    class Meta:
        db_table = "order_item"


class UserInteraction(models.Model):
    INTERACTION_CHOICES = [("click", "클릭"), ("cart", "장바구니"), ("purchase", "구매"), ("reject", "거절")]

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user             = models.ForeignKey(User, on_delete=models.CASCADE)
    product          = models.ForeignKey(Product, on_delete=models.CASCADE)
    session_id       = models.UUIDField(null=True, blank=True)
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_CHOICES)
    weight           = models.SmallIntegerField(default=1)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_interaction"
```

---

### chat/models.py

```python
import uuid
from django.db import models
from users.models import User
from pets.models import Pet
from products.models import Product


class ChatSession(models.Model):
    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_sessions")
    target_pet = models.ForeignKey(Pet, on_delete=models.SET_NULL, null=True, blank=True)
    title      = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat_session"


class ChatMessage(models.Model):
    ROLE_CHOICES = [("user", "사용자"), ("assistant", "어시스턴트")]

    message_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session    = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    role       = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_message"


class MessageProductCard(models.Model):
    id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name="product_cards")
    product = models.ForeignKey(Product, on_delete=models.RESTRICT)
    reason  = models.TextField()

    class Meta:
        db_table = "message_product_card"
```

---

## 3. settings.py 주요 설정

```python
# config/settings.py

AUTH_USER_MODEL = "users.User"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "pgvector",                 # pgvector Django 통합
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "users",
    "pets",
    "products",
    "orders",
    "chat",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST": os.environ["POSTGRES_HOST"],
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}
```

---

## 4. 마이그레이션 워크플로우

```bash
# 모델 변경 후 마이그레이션 생성
python manage.py makemigrations <앱명>

# DB 적용
python manage.py migrate

# Docker 환경에서
docker compose run --rm django python manage.py makemigrations <앱명>
docker compose run --rm django python manage.py migrate
```

> 마이그레이션 파일은 반드시 커밋한다. 팀원이 `migrate`만 실행하면 동기화됨.

---

## 5. Product 읽기 전용 + 어드민 가중치 분리

Product/Review는 데이터 파이프라인이 직접 INSERT하므로 Django Admin에서 수정 금지.
추천 가중치 등 어드민 설정은 **ProductAdminConfig** 별도 테이블에서만 수정.

```
Product (파이프라인 소유)       ProductAdminConfig (Admin 소유)
──────────────────────          ──────────────────────────────
goods_id (PK)         ◀──1:1──  product (FK)
goods_name                      admin_weight   ← Admin 수정 가능
price                           pinned         ← Admin 수정 가능
...모두 읽기 전용...             memo
                                updated_at
```

