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
