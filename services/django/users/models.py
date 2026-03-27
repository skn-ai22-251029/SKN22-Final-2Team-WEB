import uuid

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
    payment_method    = models.CharField(max_length=120, null=True, blank=True)
    marketing_consent = models.BooleanField(default=False)
    profile_image_url = models.TextField(null=True, blank=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_profile"


class SocialAccount(models.Model):
    PROVIDER_GOOGLE = "google"
    PROVIDER_NAVER = "naver"
    PROVIDER_KAKAO = "kakao"

    PROVIDER_CHOICES = [
        (PROVIDER_GOOGLE, "Google"),
        (PROVIDER_NAVER, "Naver"),
        (PROVIDER_KAKAO, "Kakao"),
    ]

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="social_accounts")
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_user_id = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    extra_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "social_account"
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_user_id"],
                name="uniq_social_account_provider_user_id",
            )
        ]


class UserPreference(models.Model):
    THEME_SYSTEM = "system"
    THEME_LIGHT = "light"
    THEME_DARK = "dark"

    THEME_CHOICES = [
        (THEME_SYSTEM, "System"),
        (THEME_LIGHT, "Light"),
        (THEME_DARK, "Dark"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name="preferences")
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default=THEME_SYSTEM)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_preference"


class UserUsedProduct(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="used_products")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="used_by_users")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_used_product"
        unique_together = [("user", "product")]
