from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.db import connection
from rest_framework import status
from rest_framework.test import APIClient

from users.models import User, UserProfile

from .breeds import _breed_meta_snapshot, resolve_breed
from .models import FuturePetProfile, Pet, PetAllergy, PetFoodPreference, PetHealthConcern


def seed_breed_meta_rows():
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO breed_meta (species, breed_name, breed_name_en)
            VALUES
                ('dog', '말티즈', 'Maltese'),
                ('cat', '브리티시 숏헤어', 'British Shorthair')
            ON CONFLICT DO NOTHING
            """
        )
    _breed_meta_snapshot.cache_clear()


class PetApiTests(TestCase):
    def setUp(self):
        seed_breed_meta_rows()
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
                "breed": "말티즈",
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
        self.assertEqual(set(pet.allergies.values_list("ingredient", flat=True)), {"닭고기", "소고기"})
        self.assertEqual(set(pet.food_preferences.values_list("food_type", flat=True)), {"dry", "wet_can"})

    def test_post_pets_rejects_invalid_allergy(self):
        response = self.client.post(
            "/api/pets/",
            {
                "name": "Bori",
                "species": "dog",
                "gender": "male",
                "weight_kg": "4.2",
                "allergies": ["왈왈"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "allergies contains an invalid value.")

    def test_post_pets_rejects_invalid_vaccination_date_format(self):
        response = self.client.post(
            "/api/pets/",
            {
                "name": "Bori",
                "species": "dog",
                "weight_kg": "4.2",
                "vaccination_date": "2026/03/01",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "vaccination_date must be a valid date.")

    def test_post_pets_allows_empty_vaccination_date(self):
        response = self.client.post(
            "/api/pets/",
            {
                "name": "Bori",
                "species": "dog",
                "weight_kg": "4.2",
                "vaccination_date": "",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        pet = Pet.objects.get(user=self.user, name="Bori")
        self.assertIsNone(pet.vaccination_date)

    def test_post_pets_rejects_vaccination_date_before_minimum(self):
        response = self.client.post(
            "/api/pets/",
            {
                "name": "Bori",
                "species": "dog",
                "weight_kg": "4.2",
                "vaccination_date": "1899-12-31",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "vaccination_date must be a valid date.")

    def test_post_pets_rejects_future_vaccination_date(self):
        response = self.client.post(
            "/api/pets/",
            {
                "name": "Bori",
                "species": "dog",
                "weight_kg": "4.2",
                "vaccination_date": (date.today() + timedelta(days=1)).isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "vaccination_date must be a valid date.")

    def test_post_pets_rejects_more_than_five_pets(self):
        for index in range(5):
            Pet.objects.create(
                user=self.user,
                name=f"Pet{index}",
                species="dog",
                gender="male",
                weight_kg=Decimal("4.0"),
                budget_range="under_5",
            )

        response = self.client.post(
            "/api/pets/",
            {"name": "Overflow", "species": "dog", "weight_kg": "4.2"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "You can register up to 5 pets.")

    def test_post_pets_rejects_unregistered_breed(self):
        response = self.client.post(
            "/api/pets/",
            {
                "name": "Bori",
                "species": "dog",
                "weight_kg": "4.2",
                "breed": "왈왈",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "breed must be one of the registered breeds.")

    def test_resolve_breed_accepts_english_name_and_spacing_variants(self):
        self.assertEqual(resolve_breed("dog", "Maltese"), "말티즈")
        self.assertEqual(resolve_breed("cat", "British Shorthair"), "브리티시 숏헤어")
        self.assertEqual(resolve_breed("cat", "British   Shorthair"), "브리티시 숏헤어")
        self.assertEqual(resolve_breed("cat", "브리티시숏헤어"), "브리티시 숏헤어")

    def test_post_pets_requires_weight(self):
        response = self.client.post(
            "/api/pets/",
            {
                "name": "Bori",
                "species": "dog",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Missing required fields: weight_kg")

    def test_post_pets_allows_empty_gender(self):
        response = self.client.post(
            "/api/pets/",
            {
                "name": "Bori",
                "species": "dog",
                "gender": "",
                "age_unknown": True,
                "weight_kg": "4.2",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        pet = Pet.objects.get(user=self.user, name="Bori")
        self.assertEqual(pet.gender, "")
        self.assertTrue(pet.age_unknown)
        self.assertEqual(pet.age_years, 0)
        self.assertEqual(pet.age_months, 0)

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
        self.assertEqual(list(pet.allergies.values_list("ingredient", flat=True)), ["연어"])
        self.assertEqual(list(pet.food_preferences.values_list("food_type", flat=True)), ["wet_pouch"])

    def test_patch_pet_rejects_null_name(self):
        pet = Pet.objects.create(
            user=self.user,
            name="Nabi",
            species="cat",
            gender="female",
            budget_range="under_5",
        )

        response = self.client.patch(
            f"/api/pets/{pet.pet_id}/",
            {"name": None},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "name is required.")
        pet.refresh_from_db()
        self.assertEqual(pet.name, "Nabi")

    def test_patch_pet_clears_optional_text_fields_with_null(self):
        pet = Pet.objects.create(
            user=self.user,
            name="Nabi",
            species="cat",
            breed="브리티시 숏헤어",
            gender="female",
            budget_range="under_5",
            special_notes="memo",
        )

        response = self.client.patch(
            f"/api/pets/{pet.pet_id}/",
            {
                "breed": None,
                "budget_range": None,
                "special_notes": None,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pet.refresh_from_db()
        self.assertIsNone(pet.breed)
        self.assertEqual(pet.budget_range, "")
        self.assertIsNone(pet.special_notes)

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


class PetPageTests(TestCase):
    def setUp(self):
        seed_breed_meta_rows()
        self.user = User.objects.create_user(email="pet-page@example.com", password="Password123!")
        UserProfile.objects.create(user=self.user, nickname="Pet Page")
        self.client.force_login(self.user)

    def test_pet_list_hides_food_preference_labels(self):
        pet = Pet.objects.create(
            user=self.user,
            name="콩이",
            species="dog",
            gender="male",
            budget_range="5_10",
        )
        PetFoodPreference.objects.create(pet=pet, food_type="dry")
        PetFoodPreference.objects.create(pet=pet, food_type="freeze_dried")

        response = self.client.get(reverse("pet_list"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "선호 사료")
        self.assertNotContains(response, "건식")
        self.assertNotContains(response, "동결건조/에어드라이")

    def test_pet_add_future_persists_profile_in_db_for_logged_in_user(self):
        response = self.client.post(
            reverse("pet_add_future"),
            {
                "preferred_species": "cat",
                "housing_type": "apartment",
                "experience_level": "experienced",
                "interests": ["food", "health"],
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"{reverse('chat')}?pet=future-profile")
        profile = FuturePetProfile.objects.get(user=self.user)
        self.assertEqual(profile.preferred_species, "cat")
        self.assertEqual(profile.housing_type, "apartment")
        self.assertEqual(profile.experience_level, "experienced")
        self.assertEqual(profile.interests, ["food", "health"])

    def test_future_pet_profile_survives_logout_and_login(self):
        FuturePetProfile.objects.create(
            user=self.user,
            preferred_species="dog",
            housing_type="house",
            experience_level="first",
            interests=["adoption"],
        )

        self.client.logout()
        self.client.login(email="pet-page@example.com", password="Password123!")

        response = self.client.get(reverse("pet_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "예비 집사")
        self.assertContains(response, "강아지 준비 중")

    def test_pet_delete_future_removes_db_profile(self):
        FuturePetProfile.objects.create(
            user=self.user,
            preferred_species="dog",
            housing_type="studio",
            experience_level="first",
            interests=["adoption"],
        )

        response = self.client.post(reverse("pet_delete_future"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("pet_list"))
        self.assertFalse(FuturePetProfile.objects.filter(user=self.user).exists())

    def test_pet_add_health_rejects_unregistered_breed(self):
        response = self.client.post(
            reverse("pet_add_health"),
            {
                "species": "dog",
                "name": "코코",
                "breed": "왈왈",
                "gender": "male",
                "age_years": "2",
                "age_months": "0",
                "weight_kg": "4",
                "neutered": "yes",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "검색 결과에 있는 품종을 선택해 주세요")
        self.assertContains(response, "왈왈")

    def test_pet_add_health_rejects_invalid_allergy(self):
        response = self.client.post(
            reverse("pet_add_health"),
            {
                "species": "dog",
                "name": "코코",
                "breed": "말티즈",
                "gender": "male",
                "age_years": "2",
                "age_months": "0",
                "weight_kg": "4",
                "neutered": "yes",
                "allergies": ["왈왈"],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "등록된 성분만 선택해 주세요")

    def test_pet_add_health_persists_selected_allergies(self):
        response = self.client.post(
            reverse("pet_add_health"),
            {
                "species": "dog",
                "name": "코코",
                "breed": "말티즈",
                "gender": "male",
                "age_years": "2",
                "age_months": "0",
                "weight_kg": "4",
                "neutered": "yes",
                "allergies": ["닭고기", "연어"],
                "final_step": "1",
            },
        )

        self.assertEqual(response.status_code, 302)
        pet = Pet.objects.get(user=self.user, name="코코")
        self.assertEqual(set(pet.allergies.values_list("ingredient", flat=True)), {"닭고기", "연어"})

    def test_pet_add_health_requires_weight(self):
        response = self.client.post(
            reverse("pet_add_health"),
            {
                "species": "dog",
                "name": "코코",
                "breed": "말티즈",
                "gender": "",
                "age_years": "2",
                "age_months": "0",
                "weight_kg": "",
                "neutered": "yes",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "몸무게를 입력해 주세요")

    def test_pet_add_health_allows_age_unknown(self):
        response = self.client.post(
            reverse("pet_add_health"),
            {
                "species": "dog",
                "name": "코코",
                "breed": "말티즈",
                "gender": "",
                "age_unknown": "yes",
                "age_years": "0",
                "age_months": "0",
                "weight_kg": "4",
                "neutered": "yes",
                "final_step": "1",
            },
        )

        self.assertEqual(response.status_code, 302)
        pet = Pet.objects.get(user=self.user, name="코코")
        self.assertTrue(pet.age_unknown)
        self.assertEqual(pet.age_years, 0)
        self.assertEqual(pet.age_months, 0)

    def test_pet_edit_renders_weight_without_trailing_decimal_zeros(self):
        pet = Pet.objects.create(
            user=self.user,
            name="코코",
            species="dog",
            breed="말티즈",
            weight_kg=Decimal("4.00"),
        )

        response = self.client.get(reverse("pet_edit", args=[pet.pet_id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="weightInput" name="weight_kg" value="4"')
