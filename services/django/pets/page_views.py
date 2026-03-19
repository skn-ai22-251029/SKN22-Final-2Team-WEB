from django.shortcuts import get_object_or_404, redirect, render

from .models import Pet, PetAllergy, PetFoodPreference, PetHealthConcern

SPECIES_OPTIONS = [
    ("dog", "강아지", "🐶"),
    ("cat", "고양이", "🐱"),
    ("future", "예비 집사", "🏠"),
]
AGE_YEAR_OPTIONS = list(range(0, 31))
AGE_MONTH_OPTIONS = list(range(0, 12))
FOOD_OPTIONS = [
    ("dry", "건식"),
    ("wet_can", "습식"),
    ("raw", "혼합/자연식"),
]
BUDGET_OPTIONS = [
    ("under_5", "5만 원 미만"),
    ("5_10", "5만 원 ~ 10만 원 미만"),
    ("10_20", "10만 원 ~ 20만 원 미만"),
    ("over_20", "20만 원 이상"),
]


def _step3_context(pet, species, step2_data=None, step3_data=None):
    step2_data = step2_data or {}
    step3_data = step3_data or {}
    return {
        "pet": pet,
        "species": species,
        "step2_data": step2_data,
        "step3_data": step3_data,
        "food_options": FOOD_OPTIONS,
        "health_options": PetHealthConcern.CONCERN_CHOICES,
        "budget_options": BUDGET_OPTIONS,
    }


def pet_list(request):
    pets = Pet.objects.filter(user=request.user) if getattr(request.user, "is_authenticated", False) else Pet.objects.none()
    return render(request, "pets/list.html", {"pets": pets})


def pet_add(request):
    return render(request, "pets/add_step1.html", {"species_options": SPECIES_OPTIONS})


def pet_add_details(request):
    species = request.GET.get("type", "dog")
    if species not in ("dog", "cat"):
        species = "dog"

    pet_seed = {
        "species": species,
        "gender": "male",
        "age_years": 0,
        "age_months": 0,
    }
    return render(
        request,
        "pets/add_step2.html",
        {
            "pet": pet_seed,
            "species": species,
            "age_year_options": AGE_YEAR_OPTIONS,
            "age_month_options": AGE_MONTH_OPTIONS,
        },
    )


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
        "gender": request.POST.get("gender", "male"),
        "age_years": int(request.POST.get("age_years", 0) or 0),
        "age_months": int(request.POST.get("age_months", 0) or 0),
        "weight_kg": request.POST.get("weight_kg", "").strip(),
        "neutered": request.POST.get("neutered", ""),
    }

    if request.POST.get("final_step") == "1":
        if not getattr(request.user, "is_authenticated", False):
            return redirect("pet_add")

        pet = Pet.objects.create(
            user=request.user,
            species=species,
            name=step2_data["name"],
            breed=step2_data["breed"] or None,
            gender=step2_data["gender"],
            age_years=step2_data["age_years"],
            age_months=step2_data["age_months"],
            weight_kg=step2_data["weight_kg"] or None,
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
            if food_type in dict(FOOD_OPTIONS):
                PetFoodPreference.objects.get_or_create(pet=pet, food_type=food_type)

        return redirect("chat")

    pet_preview = {
        "species": species,
        "name": step2_data["name"],
    }
    step3_data = {
        "vaccination_date": request.POST.get("vaccination_date", ""),
        "health_concerns": request.POST.getlist("health_concerns"),
        "allergies": request.POST.get("allergies", ""),
        "food_preferences": request.POST.getlist("food_preferences"),
        "budget_range": request.POST.get("budget_range", ""),
        "special_notes": request.POST.get("special_notes", ""),
    }
    return render(request, "pets/add_step3.html", _step3_context(pet_preview, species, step2_data, step3_data))


def pet_edit(request, pet_id):
    pet = get_object_or_404(Pet, pet_id=pet_id, user=request.user)
    if request.method == "POST":
        pet.name = request.POST.get("name", "").strip()
        pet.breed = request.POST.get("breed", "").strip() or None
        pet.gender = request.POST.get("gender", "male")
        pet.age_years = int(request.POST.get("age_years", 0) or 0)
        pet.age_months = int(request.POST.get("age_months", 0) or 0)
        pet.weight_kg = request.POST.get("weight_kg") or None
        pet.neutered = {"yes": True, "no": False}.get(request.POST.get("neutered"))
        pet.save()
        return redirect("pet_list")
    return render(
        request,
        "pets/add_step2.html",
        {
            "pet": pet,
            "species": pet.species,
            "is_edit": True,
            "age_year_options": AGE_YEAR_OPTIONS,
            "age_month_options": AGE_MONTH_OPTIONS,
        },
    )
