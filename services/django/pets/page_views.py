import json
from dataclasses import dataclass

from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .breeds import get_breed_options, resolve_breed
from .future_profile import get_future_pet_profile_for_request
from .models import FuturePetProfile, Pet, PetAllergy, PetFoodPreference, PetHealthConcern

SPECIES_OPTIONS = [
    ("dog", "강아지", "🐶"),
    ("cat", "고양이", "🐱"),
    ("future", "예비 집사", "🏠"),
]
AGE_YEAR_OPTIONS = list(range(0, 31))
AGE_MONTH_OPTIONS = list(range(0, 12))
DOG_FOOD_OPTIONS = [
    ("dry", "건식"),
    ("cooked", "화식"),
    ("soft", "소프트"),
    ("wet_can", "습식"),
    ("freeze_dried", "동결건조/에어드라이"),
]
CAT_FOOD_OPTIONS = [
    ("dry", "건식"),
    ("wet_can", "주식캔"),
    ("wet_pouch", "주식파우치"),
    ("freeze_dried", "에어/동결건조"),
]
FUTURE_HOUSING_OPTIONS = [
    ("studio", "원룸"),
    ("apartment", "아파트"),
    ("house", "주택"),
    ("other", "기타"),
]
FUTURE_EXPERIENCE_OPTIONS = [
    ("first", "처음"),
    ("experienced", "경험 있음"),
]
FUTURE_INTEREST_OPTIONS = [
    ("adoption", "입양 준비"),
    ("breed_personality", "품종/성격"),
    ("initial_cost", "초기 비용"),
    ("starter_items", "필수 용품"),
    ("food", "사료"),
    ("health", "건강관리"),
    ("training", "훈련/교육"),
]
BUDGET_OPTIONS = [
    ("under_5", "5만 원 미만"),
    ("5_10", "5만 원 ~ 10만 원 미만"),
    ("10_20", "10만 원 ~ 20만 원 미만"),
    ("over_20", "20만 원 이상"),
]


def _food_options_for_species(species):
    if species == "dog":
        return DOG_FOOD_OPTIONS
    return CAT_FOOD_OPTIONS


def _food_preference_labels(food_values, species):
    label_map = dict(_food_options_for_species(species))
    fallback_label_map = dict(PetFoodPreference.FOOD_TYPE_CHOICES)
    return [label_map.get(value, fallback_label_map.get(value, value)) for value in food_values]


def _breed_error_message(species):
    return "검색 결과에 있는 품종을 선택해 주세요"


def _weight_error_message():
    return "몸무게를 입력해 주세요"


def _normalize_gender(value):
    normalized = (value or "").strip()
    return normalized if normalized in {"male", "female"} else ""


def _breed_options_json():
    return json.dumps({
        "dog": get_breed_options("dog"),
        "cat": get_breed_options("cat"),
    })


def _render_step2_form(
    request,
    *,
    pet,
    species,
    step3_data=None,
    is_edit=False,
    is_preview_edit=False,
    breed_error_message="",
    weight_error_message="",
):
    return render(
        request,
        "pets/add_step2.html",
        {
            "pet": pet,
            "species": species,
            "breed_options_json": _breed_options_json(),
            "age_year_options": AGE_YEAR_OPTIONS,
            "age_month_options": AGE_MONTH_OPTIONS,
            "step3_data": step3_data or {},
            "is_edit": is_edit,
            "is_preview_edit": is_preview_edit,
            "breed_error_message": breed_error_message,
            "weight_error_message": weight_error_message,
        },
    )


@dataclass
class PetPreview:
    pet_id: str
    name: str
    species: str
    breed: str | None
    gender: str
    age_unknown: bool
    age_years: int
    age_months: int

    def get_species_display(self):
        return dict(Pet.SPECIES_CHOICES).get(self.species, self.species)

    def get_gender_display(self):
        return dict(Pet.GENDER_CHOICES).get(self.gender, self.gender)


def _preview_pets():
    return [
        PetPreview(
            pet_id="preview-dog",
            name="콩이",
            species="dog",
            breed="말티즈",
            gender="male",
            age_unknown=False,
            age_years=2,
            age_months=3,
        ),
        PetPreview(
            pet_id="preview-cat",
            name="모찌",
            species="cat",
            breed="브리티시 숏헤어",
            gender="female",
            age_unknown=False,
            age_years=1,
            age_months=8,
        ),
        PetPreview(
            pet_id="preview-dog-2",
            name="보리",
            species="dog",
            breed="푸들",
            gender="female",
            age_unknown=False,
            age_years=5,
            age_months=1,
        ),
        PetPreview(
            pet_id="preview-cat-2",
            name="라떼",
            species="cat",
            breed="코리안 숏헤어",
            gender="male",
            age_unknown=False,
            age_years=3,
            age_months=4,
        ),
    ]


def _get_preview_pet(pet_id):
    return next((pet for pet in _preview_pets() if pet.pet_id == pet_id), None)


def _preview_step3_data(pet):
    defaults = {
        "preview-dog": {
            "vaccination_date": "2025-11-12",
            "health_concerns": ["skin", "dental"],
            "allergies": "닭고기,밀",
            "food_preferences": ["dry", "raw"],
            "budget_range": "5_10",
            "special_notes": "피부가 예민해서 원료가 단순한 사료를 선호합니다.",
        },
        "preview-cat": {
            "vaccination_date": "2026-01-08",
            "health_concerns": ["hairball", "urinary"],
            "allergies": "참치",
            "food_preferences": ["wet_can"],
            "budget_range": "under_5",
            "special_notes": "물 섭취량이 적어서 습식 위주 급여 중입니다.",
        },
        "preview-dog-2": {
            "vaccination_date": "2025-10-04",
            "health_concerns": ["joint", "weight"],
            "allergies": "오리",
            "food_preferences": ["dry"],
            "budget_range": "10_20",
            "special_notes": "관절 관리 중이라 체중 유지가 중요합니다.",
        },
        "preview-cat-2": {
            "vaccination_date": "2025-12-21",
            "health_concerns": ["eye"],
            "allergies": "",
            "food_preferences": ["wet_can", "raw"],
            "budget_range": "5_10",
            "special_notes": "눈물이 자주 생겨서 관련 성분을 신경 쓰고 있습니다.",
        },
    }
    return defaults.get(
        pet.pet_id,
        {
            "vaccination_date": "",
            "health_concerns": [],
            "allergies": "",
            "food_preferences": [],
            "budget_range": "",
            "special_notes": "",
        },
    )


def _step3_context(pet, species, step2_data=None, step3_data=None):
    step2_data = step2_data or {}
    step3_data = step3_data or {}
    return {
        "pet": pet,
        "species": species,
        "step2_data": step2_data,
        "step3_data": step3_data,
        "food_options": _food_options_for_species(species),
        "health_options": PetHealthConcern.CONCERN_CHOICES,
        "budget_options": BUDGET_OPTIONS,
    }


def _pet_step2_data(pet):
    return {
        "species": pet.species,
        "name": pet.name,
        "breed": pet.breed or "",
        "gender": pet.gender,
        "age_unknown": pet.age_unknown,
        "age_years": pet.age_years,
        "age_months": pet.age_months,
        "weight_kg": "" if pet.weight_kg is None else str(pet.weight_kg),
        "neutered": "yes" if pet.neutered is True else "no" if pet.neutered is False else "",
    }


def _pet_step3_data(pet):
    return {
        "vaccination_date": pet.vaccination_date.isoformat() if pet.vaccination_date else "",
        "health_concerns": list(pet.health_concerns.values_list("concern", flat=True)),
        "allergies": ",".join(pet.allergies.values_list("ingredient", flat=True)),
        "food_preferences": list(pet.food_preferences.values_list("food_type", flat=True)),
        "budget_range": pet.budget_range or "",
        "special_notes": pet.special_notes or "",
    }


def _future_pet_list_item(profile):
    if not profile:
        return None

    housing_labels = {
        "studio": "원룸",
        "apartment": "아파트",
        "house": "주택",
        "other": "기타",
    }
    experience_labels = {
        "first": "처음",
        "experienced": "경험 있음",
    }

    preferred_species = profile.get("preferred_species", "")
    if preferred_species == "dog":
        summary = "강아지 준비 중"
    elif preferred_species == "cat":
        summary = "고양이 준비 중"
    else:
        summary = "입양 준비 중"

    return {
        "pet_id": "future-profile",
        "name": "예비 집사",
        "species": "future",
        "emoji": "🏠",
        "summary": summary,
        "detail": " · ".join(
            value
            for value in [
                housing_labels.get(profile.get("housing_type", ""), ""),
                experience_labels.get(profile.get("experience_level", ""), ""),
            ]
            if value
        )
        or "입양 준비 상담 프로필",
        "is_future_profile": True,
    }


def _sort_pet_list_items(pets):
    def _species_of(pet):
        return pet.get("species", "") if isinstance(pet, dict) else getattr(pet, "species", "")

    def _created_at_of(pet):
        return pet.get("created_at") if isinstance(pet, dict) else getattr(pet, "created_at", None)

    return sorted(
        pets,
        key=lambda pet: (
            _species_of(pet) == "future",
            _created_at_of(pet),
        ),
    )


def pet_list(request):
    is_preview_list = request.GET.get("preview") == "filled"
    future_pet = None
    if is_preview_list:
        pets = _preview_pets()
        actual_pet_count = len(pets)
    elif getattr(request.user, "is_authenticated", False):
        pets = list(Pet.objects.filter(user=request.user).prefetch_related("food_preferences"))
        actual_pet_count = len(pets)
        future_pet = _future_pet_list_item(get_future_pet_profile_for_request(request))
        for pet in pets:
            pet.food_preference_labels = _food_preference_labels(
                list(pet.food_preferences.values_list("food_type", flat=True)),
                pet.species,
            )
        if future_pet:
            pets.append(future_pet)
        pets = _sort_pet_list_items(pets)
    else:
        pets = []
        actual_pet_count = 0
    return render(
        request,
        "pets/list.html",
        {
            "pets": pets,
            "is_preview_list": is_preview_list,
            "actual_pet_count": actual_pet_count,
            "has_future_pet": bool(future_pet),
        },
    )


def pet_add(request):
    return render(request, "pets/add_step1.html", {"species_options": SPECIES_OPTIONS})


def pet_add_future(request):
    if request.method == "POST":
        future_profile_data = {
            "preferred_species": request.POST.get("preferred_species", "").strip(),
            "housing_type": request.POST.get("housing_type", "").strip(),
            "experience_level": request.POST.get("experience_level", "").strip(),
            "interests": request.POST.getlist("interests"),
        }
        if getattr(request.user, "is_authenticated", False):
            FuturePetProfile.objects.update_or_create(
                user=request.user,
                defaults=future_profile_data,
            )
            request.session.pop("future_pet_profile", None)
        else:
            request.session["future_pet_profile"] = future_profile_data
        return redirect(f"{reverse('chat')}?pet=future-profile")

    future_profile = {
        "preferred_species": "",
        "housing_type": "",
        "experience_level": "",
        "interests": [],
    } | (get_future_pet_profile_for_request(request) or {})
    return render(
        request,
        "pets/add_future.html",
        {
            "future_profile": future_profile,
            "housing_options": FUTURE_HOUSING_OPTIONS,
            "experience_options": FUTURE_EXPERIENCE_OPTIONS,
            "interest_options": FUTURE_INTEREST_OPTIONS,
        },
    )


def pet_delete_future(request):
    if request.method == "POST":
        if getattr(request.user, "is_authenticated", False):
            FuturePetProfile.objects.filter(user=request.user).delete()
        request.session.pop("future_pet_profile", None)
    return redirect("pet_list")


def pet_add_details(request):
    species = request.GET.get("type", "dog")
    if species not in ("dog", "cat"):
        species = "dog"

    pet_seed = {
        "species": species,
        "name": request.GET.get("name", "").strip(),
        "breed": request.GET.get("breed", "").strip(),
        "gender": _normalize_gender(request.GET.get("gender", "")),
        "age_unknown": request.GET.get("age_unknown") == "yes",
        "age_years": 0 if request.GET.get("age_unknown") == "yes" else int(request.GET.get("age_years", 0) or 0),
        "age_months": 0 if request.GET.get("age_unknown") == "yes" else int(request.GET.get("age_months", 0) or 0),
        "weight_kg": request.GET.get("weight_kg", "").strip(),
        "neutered": True if request.GET.get("neutered") == "yes" else False if request.GET.get("neutered") == "no" else None,
    }
    step3_data = {
        "vaccination_date": request.GET.get("vaccination_date", "").strip(),
        "health_concerns": request.GET.getlist("health_concerns"),
        "allergies": request.GET.get("allergies", "").strip(),
        "food_preferences": request.GET.getlist("food_preferences"),
        "budget_range": request.GET.get("budget_range", "").strip(),
        "special_notes": request.GET.get("special_notes", "").strip(),
    }
    return _render_step2_form(request, pet=pet_seed, species=species, step3_data=step3_data)


def pet_add_health(request):
    if request.method != "POST":
        return redirect("pet_add")

    species = request.POST.get("species", "dog")
    if species not in ("dog", "cat"):
        return redirect("pet_add")

    step2_data = {
        "species": species,
        "name": request.POST.get("name", "").strip(),
        "breed": request.POST.get("breed", "").strip(),
        "gender": _normalize_gender(request.POST.get("gender", "")),
        "age_unknown": request.POST.get("age_unknown") == "yes",
        "age_years": 0 if request.POST.get("age_unknown") == "yes" else int(request.POST.get("age_years", 0) or 0),
        "age_months": 0 if request.POST.get("age_unknown") == "yes" else int(request.POST.get("age_months", 0) or 0),
        "weight_kg": request.POST.get("weight_kg", "").strip(),
        "neutered": request.POST.get("neutered", ""),
    }
    step3_data = {
        "vaccination_date": request.POST.get("vaccination_date", "").strip(),
        "health_concerns": request.POST.getlist("health_concerns"),
        "allergies": request.POST.get("allergies", "").strip(),
        "food_preferences": request.POST.getlist("food_preferences"),
        "budget_range": request.POST.get("budget_range", "").strip(),
        "special_notes": request.POST.get("special_notes", "").strip(),
    }
    weight_error = ""
    if not step2_data["weight_kg"]:
        weight_error = _weight_error_message()
    resolved_breed = resolve_breed(species, step2_data["breed"])
    if not resolved_breed or weight_error:
        pet_preview = {
            "species": species,
            "name": step2_data["name"],
            "breed": step2_data["breed"],
            "gender": step2_data["gender"],
            "age_unknown": step2_data["age_unknown"],
            "age_years": step2_data["age_years"],
            "age_months": step2_data["age_months"],
            "weight_kg": step2_data["weight_kg"],
            "neutered": True if step2_data["neutered"] == "yes" else False if step2_data["neutered"] == "no" else None,
        }
        return _render_step2_form(
            request,
            pet=pet_preview,
            species=species,
            step3_data=step3_data,
            breed_error_message="" if resolved_breed else _breed_error_message(species),
            weight_error_message=weight_error,
        )
    step2_data["breed"] = resolved_breed

    if request.POST.get("final_step") == "1":
        if not getattr(request.user, "is_authenticated", False):
            return redirect("pet_add")

        pet = Pet.objects.create(
            user=request.user,
            species=species,
            name=step2_data["name"],
            breed=step2_data["breed"] or None,
            gender=step2_data["gender"],
            age_unknown=step2_data["age_unknown"],
            age_years=step2_data["age_years"],
            age_months=step2_data["age_months"],
            weight_kg=step2_data["weight_kg"],
            neutered={"yes": True, "no": False}.get(step2_data["neutered"]),
            vaccination_date=request.POST.get("vaccination_date") or None,
            budget_range=request.POST.get("budget_range", ""),
            special_notes=request.POST.get("special_notes", "").strip() or None,
        )

        for concern in request.POST.getlist("health_concerns"):
            if concern in dict(PetHealthConcern.CONCERN_CHOICES):
                PetHealthConcern.objects.get_or_create(pet=pet, concern=concern)

        for ingredient in [item.strip() for item in request.POST.get("allergies", "").split(",") if item.strip()]:
            PetAllergy.objects.get_or_create(pet=pet, ingredient=ingredient)

        for food_type in request.POST.getlist("food_preferences"):
            if food_type in dict(_food_options_for_species(species)):
                PetFoodPreference.objects.get_or_create(pet=pet, food_type=food_type)

        return redirect("chat")

    pet_preview = {
        "species": species,
        "name": step2_data["name"],
    }
    return render(request, "pets/add_step3.html", _step3_context(pet_preview, species, step2_data, step3_data))


def pet_edit(request, pet_id):
    pet = get_object_or_404(Pet, pet_id=pet_id, user=request.user)
    if request.method == "POST":
        step2_data = {
            "species": pet.species,
            "name": request.POST.get("name", "").strip(),
            "breed": request.POST.get("breed", "").strip(),
            "gender": _normalize_gender(request.POST.get("gender", "")),
            "age_unknown": request.POST.get("age_unknown") == "yes",
            "age_years": 0 if request.POST.get("age_unknown") == "yes" else int(request.POST.get("age_years", 0) or 0),
            "age_months": 0 if request.POST.get("age_unknown") == "yes" else int(request.POST.get("age_months", 0) or 0),
            "weight_kg": request.POST.get("weight_kg", "").strip(),
            "neutered": request.POST.get("neutered", ""),
        }
        return render(
            request,
            "pets/add_step3.html",
            _step3_context(
                {"species": pet.species, "name": step2_data["name"]},
                pet.species,
                step2_data,
                _pet_step3_data(pet),
            )
            | {"is_edit": True, "pet_id": pet.pet_id},
        )
    return _render_step2_form(request, pet=pet, species=pet.species, is_edit=True)


def pet_edit_health(request, pet_id):
    pet = get_object_or_404(Pet, pet_id=pet_id, user=request.user)
    if request.method != "POST":
        return redirect("pet_edit", pet_id=pet.pet_id)

    weight_value = request.POST.get("weight_kg", "").strip()
    resolved_breed = resolve_breed(pet.species, request.POST.get("breed", "").strip())
    if not resolved_breed or not weight_value:
        return _render_step2_form(
            request,
            pet={
                "species": pet.species,
                "name": request.POST.get("name", "").strip(),
                "breed": request.POST.get("breed", "").strip(),
                "gender": _normalize_gender(request.POST.get("gender", "")),
                "age_unknown": request.POST.get("age_unknown") == "yes",
                "age_years": 0 if request.POST.get("age_unknown") == "yes" else int(request.POST.get("age_years", 0) or 0),
                "age_months": 0 if request.POST.get("age_unknown") == "yes" else int(request.POST.get("age_months", 0) or 0),
                "weight_kg": weight_value,
                "neutered": {"yes": True, "no": False}.get(request.POST.get("neutered", "")),
            },
            species=pet.species,
            is_edit=True,
            breed_error_message="" if resolved_breed else _breed_error_message(pet.species),
            weight_error_message="" if weight_value else _weight_error_message(),
        )

    pet.name = request.POST.get("name", "").strip()
    pet.breed = resolved_breed
    pet.gender = _normalize_gender(request.POST.get("gender", ""))
    pet.age_unknown = request.POST.get("age_unknown") == "yes"
    pet.age_years = 0 if pet.age_unknown else int(request.POST.get("age_years", 0) or 0)
    pet.age_months = 0 if pet.age_unknown else int(request.POST.get("age_months", 0) or 0)
    pet.weight_kg = weight_value
    pet.neutered = {"yes": True, "no": False}.get(request.POST.get("neutered"))
    pet.vaccination_date = request.POST.get("vaccination_date") or None
    pet.budget_range = request.POST.get("budget_range", "")
    pet.special_notes = request.POST.get("special_notes", "").strip() or None
    pet.save()

    PetHealthConcern.objects.filter(pet=pet).delete()
    for concern in request.POST.getlist("health_concerns"):
        if concern in dict(PetHealthConcern.CONCERN_CHOICES):
            PetHealthConcern.objects.get_or_create(pet=pet, concern=concern)

    PetAllergy.objects.filter(pet=pet).delete()
    for ingredient in [item.strip() for item in request.POST.get("allergies", "").split(",") if item.strip()]:
        PetAllergy.objects.get_or_create(pet=pet, ingredient=ingredient)

    PetFoodPreference.objects.filter(pet=pet).delete()
    valid_food_types = {value for value, _ in PetFoodPreference.FOOD_TYPE_CHOICES}
    for food_type in request.POST.getlist("food_preferences"):
        if food_type in valid_food_types:
            PetFoodPreference.objects.get_or_create(pet=pet, food_type=food_type)

    return redirect("pet_list")


def preview_pet_edit(request, pet_id):
    pet = _get_preview_pet(pet_id)
    if pet is None:
        return redirect("pet_list")

    if request.method == "POST":
        step2_data = {
            "species": pet.species,
            "name": request.POST.get("name", "").strip(),
            "breed": request.POST.get("breed", "").strip(),
            "gender": _normalize_gender(request.POST.get("gender", "")),
            "age_unknown": request.POST.get("age_unknown") == "yes",
            "age_years": 0 if request.POST.get("age_unknown") == "yes" else int(request.POST.get("age_years", 0) or 0),
            "age_months": 0 if request.POST.get("age_unknown") == "yes" else int(request.POST.get("age_months", 0) or 0),
            "weight_kg": request.POST.get("weight_kg", "").strip(),
            "neutered": request.POST.get("neutered", ""),
        }
        resolved_breed = resolve_breed(pet.species, step2_data["breed"])
        if not resolved_breed or not step2_data["weight_kg"]:
            return _render_step2_form(
                request,
                pet={
                    "species": pet.species,
                    "name": step2_data["name"],
                    "breed": step2_data["breed"],
                    "gender": step2_data["gender"],
                    "age_unknown": step2_data["age_unknown"],
                    "age_years": step2_data["age_years"],
                    "age_months": step2_data["age_months"],
                    "weight_kg": step2_data["weight_kg"],
                    "neutered": True if step2_data["neutered"] == "yes" else False if step2_data["neutered"] == "no" else None,
                },
                species=pet.species,
                is_edit=True,
                is_preview_edit=True,
                breed_error_message="" if resolved_breed else _breed_error_message(pet.species),
                weight_error_message="" if step2_data["weight_kg"] else _weight_error_message(),
            )
        step2_data["breed"] = resolved_breed
        return render(
            request,
            "pets/add_step3.html",
            _step3_context(
                {"species": pet.species, "name": step2_data["name"]},
                pet.species,
                step2_data,
                _preview_step3_data(pet),
            )
            | {"is_edit": True, "is_preview_edit": True, "pet_id": pet.pet_id},
        )

    return _render_step2_form(request, pet=pet, species=pet.species, is_edit=True, is_preview_edit=True)


def preview_pet_edit_health(request, pet_id):
    if request.method != "POST":
        return redirect("pet_list")
    return redirect("/pets/?preview=filled")
