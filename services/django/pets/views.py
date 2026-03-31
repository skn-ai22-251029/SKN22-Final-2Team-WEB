from datetime import date
from decimal import Decimal, InvalidOperation

from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from .breeds import resolve_breed
from .models import Pet, PetAllergy, PetFoodPreference, PetHealthConcern


def serialize_pet(pet):
    return {
        "pet_id": str(pet.pet_id),
        "name": pet.name,
        "species": pet.species,
        "breed": pet.breed,
        "gender": pet.gender,
        "age_years": pet.age_years,
        "age_months": pet.age_months,
        "weight_kg": str(pet.weight_kg) if pet.weight_kg is not None else None,
        "neutered": pet.neutered,
        "vaccination_date": pet.vaccination_date.isoformat() if pet.vaccination_date else None,
        "budget_range": pet.budget_range,
        "special_notes": pet.special_notes,
        "health_concerns": [item.concern for item in pet.health_concerns.order_by("concern")],
        "allergies": [item.ingredient for item in pet.allergies.order_by("ingredient")],
        "food_preferences": [item.food_type for item in pet.food_preferences.order_by("food_type")],
        "created_at": pet.created_at,
        "updated_at": pet.updated_at,
    }


def _parse_integer(value, field_name):
    if value in (None, ""):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer.") from exc


def _parse_decimal(value, field_name):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a decimal number.") from exc


def _parse_boolean(value):
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError("neutered must be a boolean.")


def _parse_vaccination_date(value):
    if value in (None, ""):
        return None

    if not isinstance(value, str):
        raise ValueError("vaccination_date must be a valid date.")

    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("vaccination_date must be a valid date.") from exc

    if parsed < date(1900, 1, 1) or parsed > date.today():
        raise ValueError("vaccination_date must be a valid date.")

    return parsed


def _get_list_value(request, field_name):
    if hasattr(request.data, "getlist"):
        values = request.data.getlist(field_name)
        if len(values) > 1:
            return values

    value = request.data.get(field_name)
    if value is None:
        return None
    if isinstance(value, list):
        return value
    return [value]


def _parse_allergies(raw_values):
    if raw_values is None:
        return None

    if len(raw_values) == 1 and isinstance(raw_values[0], str) and "," in raw_values[0]:
        raw_values = raw_values[0].split(",")

    cleaned = []
    for value in raw_values:
        ingredient = str(value).strip()
        if ingredient and ingredient not in cleaned:
            cleaned.append(ingredient)
    return cleaned


def _parse_choice_list(raw_values, valid_values, field_name):
    if raw_values is None:
        return None

    cleaned = []
    for value in raw_values:
        choice = str(value).strip()
        if choice not in valid_values:
            raise ValueError(f"{field_name} contains an invalid value: {choice}")
        if choice not in cleaned:
            cleaned.append(choice)
    return cleaned


def _replace_related_items(model, pet, field_name, attr_name, values):
    model.objects.filter(pet=pet).delete()
    if values is None:
        return
    for value in values:
        model.objects.create(pet=pet, **{field_name: value})


def _apply_pet_payload(pet, request, *, partial):
    required_fields = ["name", "species", "gender"]
    if not partial:
        missing = [field for field in required_fields if request.data.get(field) in (None, "")]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

    if "name" in request.data:
        name = str(request.data.get("name", "")).strip()
        if not name:
            raise ValueError("name is required.")
        pet.name = name

    if "species" in request.data:
        species = request.data.get("species")
        valid_species = {choice for choice, _ in Pet.SPECIES_CHOICES}
        if species not in valid_species:
            raise ValueError("species must be one of: cat, dog.")
        pet.species = species

    if "gender" in request.data:
        gender = request.data.get("gender")
        valid_genders = {choice for choice, _ in Pet.GENDER_CHOICES}
        if gender not in valid_genders:
            raise ValueError("gender must be one of: male, female.")
        pet.gender = gender

    scalar_fields = {
        "age_years": lambda value: _parse_integer(value, "age_years"),
        "age_months": lambda value: _parse_integer(value, "age_months"),
        "weight_kg": lambda value: _parse_decimal(value, "weight_kg"),
        "neutered": _parse_boolean,
        "vaccination_date": _parse_vaccination_date,
        "budget_range": lambda value: str(value).strip(),
        "special_notes": lambda value: str(value).strip() or None,
    }

    for field, parser in scalar_fields.items():
        if field in request.data:
            setattr(pet, field, parser(request.data.get(field)))

    if "breed" in request.data:
        resolved_breed = resolve_breed(pet.species, request.data.get("breed"))
        if not resolved_breed:
            raise ValueError("breed must be one of the registered breeds.")
        pet.breed = resolved_breed

    valid_health_concerns = {choice for choice, _ in PetHealthConcern.CONCERN_CHOICES}
    valid_food_preferences = {choice for choice, _ in PetFoodPreference.FOOD_TYPE_CHOICES}

    return {
        "health_concerns": _parse_choice_list(
            _get_list_value(request, "health_concerns"),
            valid_health_concerns,
            "health_concerns",
        ),
        "allergies": _parse_allergies(_get_list_value(request, "allergies")),
        "food_preferences": _parse_choice_list(
            _get_list_value(request, "food_preferences"),
            valid_food_preferences,
            "food_preferences",
        ),
    }


class PetListView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pets = (
            Pet.objects.filter(user=request.user)
            .prefetch_related("health_concerns", "allergies", "food_preferences")
            .order_by("created_at")
        )
        return Response({"pets": [serialize_pet(pet) for pet in pets]})

    def post(self, request):
        if request.user.pets.count() >= 5:
            return Response({"detail": "You can register up to 5 pets."}, status=status.HTTP_400_BAD_REQUEST)

        pet = Pet(user=request.user, budget_range="")
        try:
            related_payload = _apply_pet_payload(pet, request, partial=False)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        pet.save()
        _replace_related_items(PetHealthConcern, pet, "concern", "health_concerns", related_payload["health_concerns"])
        _replace_related_items(PetAllergy, pet, "ingredient", "allergies", related_payload["allergies"])
        _replace_related_items(
            PetFoodPreference,
            pet,
            "food_type",
            "food_preferences",
            related_payload["food_preferences"],
        )
        pet.refresh_from_db()
        return Response({"pet": serialize_pet(pet)}, status=status.HTTP_201_CREATED)


class PetDetailView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def _delete_pet(self, request, pet_id, *, redirect_to_list=False):
        pet = get_object_or_404(Pet, pet_id=pet_id, user=request.user)
        pet.delete()
        if redirect_to_list:
            return HttpResponseRedirect(reverse("pet_list"))
        return Response(status=status.HTTP_204_NO_CONTENT)

    def patch(self, request, pet_id):
        pet = get_object_or_404(
            Pet.objects.prefetch_related("health_concerns", "allergies", "food_preferences"),
            pet_id=pet_id,
            user=request.user,
        )
        try:
            related_payload = _apply_pet_payload(pet, request, partial=True)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        pet.save()

        if related_payload["health_concerns"] is not None:
            _replace_related_items(PetHealthConcern, pet, "concern", "health_concerns", related_payload["health_concerns"])
        if related_payload["allergies"] is not None:
            _replace_related_items(PetAllergy, pet, "ingredient", "allergies", related_payload["allergies"])
        if related_payload["food_preferences"] is not None:
            _replace_related_items(
                PetFoodPreference,
                pet,
                "food_type",
                "food_preferences",
                related_payload["food_preferences"],
            )

        pet.refresh_from_db()
        return Response({"pet": serialize_pet(pet)})

    def delete(self, request, pet_id):
        return self._delete_pet(request, pet_id)

    def post(self, request, pet_id):
        if request.data.get("_method", "").upper() == "DELETE":
            return self._delete_pet(request, pet_id, redirect_to_list=True)
        return Response({"detail": "Method not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
