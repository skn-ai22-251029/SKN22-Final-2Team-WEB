from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from users.models import User, UserProfile

from .models import Pet, PetAllergy, PetFoodPreference, PetHealthConcern


class PetApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="pet-owner@example.com", password="Password123!")
        UserProfile.objects.create(user=self.user, nickname="Pet Owner")
        self.client.force_authenticate(self.user)

    def test_get_pets_returns_only_my_pets(self):
        my_pet = Pet.objects.create(
            user=self.user,
            name="Nabi",
            species="cat",
            gender="female",
            budget_range="5_10",
        )
        PetHealthConcern.objects.create(pet=my_pet, concern="skin")
        PetAllergy.objects.create(pet=my_pet, ingredient="chicken")
        PetFoodPreference.objects.create(pet=my_pet, food_type="dry")

        other_user = User.objects.create_user(email="other@example.com", password="Password123!")
        UserProfile.objects.create(user=other_user, nickname="Other")
        Pet.objects.create(user=other_user, name="Bori", species="dog", gender="male", budget_range="under_5")

        response = self.client.get("/api/pets/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["pets"]), 1)
        self.assertEqual(response.data["pets"][0]["name"], "Nabi")
        self.assertEqual(response.data["pets"][0]["health_concerns"], ["skin"])
        self.assertEqual(response.data["pets"][0]["allergies"], ["chicken"])
        self.assertEqual(response.data["pets"][0]["food_preferences"], ["dry"])

    def test_post_pets_creates_pet_with_multi_value_fields(self):
        response = self.client.post(
            "/api/pets/",
            {
                "name": "Bori",
                "species": "dog",
                "gender": "male",
                "breed": "Maltese",
                "age_years": 3,
                "age_months": 2,
                "weight_kg": "4.20",
                "neutered": True,
                "vaccination_date": "2026-03-01",
                "budget_range": "5_10",
                "special_notes": "likes walks",
                "health_concerns": ["skin", "joint"],
                "allergies": ["chicken", "beef"],
                "food_preferences": ["dry", "wet_can"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        pet = Pet.objects.get(user=self.user, name="Bori")
        self.assertEqual(pet.weight_kg, Decimal("4.20"))
        self.assertEqual(set(pet.health_concerns.values_list("concern", flat=True)), {"skin", "joint"})
        self.assertEqual(set(pet.allergies.values_list("ingredient", flat=True)), {"chicken", "beef"})
        self.assertEqual(set(pet.food_preferences.values_list("food_type", flat=True)), {"dry", "wet_can"})

    def test_post_pets_rejects_more_than_five_pets(self):
        for index in range(5):
            Pet.objects.create(
                user=self.user,
                name=f"Pet{index}",
                species="dog",
                gender="male",
                budget_range="under_5",
            )

        response = self.client.post(
            "/api/pets/",
            {"name": "Overflow", "species": "dog", "gender": "male"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "You can register up to 5 pets.")

    def test_patch_pet_updates_fields_and_replaces_multi_value_fields(self):
        pet = Pet.objects.create(
            user=self.user,
            name="Nabi",
            species="cat",
            gender="female",
            budget_range="under_5",
        )
        PetHealthConcern.objects.create(pet=pet, concern="skin")
        PetAllergy.objects.create(pet=pet, ingredient="chicken")
        PetFoodPreference.objects.create(pet=pet, food_type="dry")

        response = self.client.patch(
            f"/api/pets/{pet.pet_id}/",
            {
                "name": "Nabi Updated",
                "budget_range": "10_20",
                "health_concerns": ["joint", "digestion"],
                "allergies": ["salmon"],
                "food_preferences": ["wet_pouch"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pet.refresh_from_db()
        self.assertEqual(pet.name, "Nabi Updated")
        self.assertEqual(pet.budget_range, "10_20")
        self.assertEqual(set(pet.health_concerns.values_list("concern", flat=True)), {"joint", "digestion"})
        self.assertEqual(list(pet.allergies.values_list("ingredient", flat=True)), ["salmon"])
        self.assertEqual(list(pet.food_preferences.values_list("food_type", flat=True)), ["wet_pouch"])

    def test_delete_pet_removes_pet(self):
        pet = Pet.objects.create(
            user=self.user,
            name="Delete Me",
            species="dog",
            gender="male",
            budget_range="under_5",
        )

        response = self.client.delete(f"/api/pets/{pet.pet_id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Pet.objects.filter(pet_id=pet.pet_id).exists())

    def test_post_delete_override_supports_template_form(self):
        pet = Pet.objects.create(
            user=self.user,
            name="Delete Form",
            species="dog",
            gender="male",
            budget_range="under_5",
        )

        response = self.client.post(f"/api/pets/{pet.pet_id}/", {"_method": "DELETE"})

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response["Location"], "/pets/")
        self.assertFalse(Pet.objects.filter(pet_id=pet.pet_id).exists())

    def test_session_authenticated_post_delete_override_supports_template_form(self):
        pet = Pet.objects.create(
            user=self.user,
            name="Delete Session Form",
            species="dog",
            gender="male",
            budget_range="under_5",
        )
        self.client.force_authenticate(user=None)
        self.client.login(email="pet-owner@example.com", password="Password123!")

        response = self.client.post(f"/api/pets/{pet.pet_id}/", {"_method": "DELETE"})

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response["Location"], "/pets/")
        self.assertFalse(Pet.objects.filter(pet_id=pet.pet_id).exists())
