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
    gender           = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, default="")
    age_unknown      = models.BooleanField(default=False)
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


class FuturePetProfile(models.Model):
    user             = models.OneToOneField(User, on_delete=models.CASCADE, related_name="future_pet_profile")
    preferred_species = models.CharField(max_length=20, blank=True, default="")
    housing_type      = models.CharField(max_length=20, blank=True, default="")
    experience_level  = models.CharField(max_length=20, blank=True, default="")
    interests         = models.JSONField(default=list, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "future_pet_profile"


class PetHealthConcern(models.Model):
    CONCERN_CHOICES = [
        ("skin", "피부"), ("joint", "관절"), ("digestion", "소화"), ("weight", "체중"),
        ("urinary", "요로"), ("eye", "눈물"), ("hairball", "헤어볼"), ("dental", "치아"), ("immunity", "면역"),
    ]
    id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pet     = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="health_concerns")
    concern = models.CharField(max_length=20, choices=CONCERN_CHOICES)

    class Meta:
        db_table = "pet_health_concern"
        unique_together = [("pet", "concern")]


class PetAllergy(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pet        = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="allergies")
    ingredient = models.CharField(max_length=100)

    class Meta:
        db_table = "pet_allergy"
        unique_together = [("pet", "ingredient")]


class PetFoodPreference(models.Model):
    FOOD_TYPE_CHOICES = [
        ("dry", "건식"),
        ("wet_can", "습식"),
        ("wet_pouch", "습식파우치"),
        ("freeze_dried", "동결건조/에어드라이"),
        ("raw", "혼합/자연식"),
        ("soft", "소프트"),
        ("cooked", "화식"),
    ]
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pet       = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="food_preferences")
    food_type = models.CharField(max_length=20, choices=FOOD_TYPE_CHOICES)

    class Meta:
        db_table = "pet_food_preference"
        unique_together = [("pet", "food_type")]


class PetUsedProduct(models.Model):
    id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pet     = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="used_products")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="used_by_pets")

    class Meta:
        db_table = "pet_used_product"
        unique_together = [("pet", "product")]
