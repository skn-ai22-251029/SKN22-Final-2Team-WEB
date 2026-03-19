from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Pet

SPECIES_OPTIONS = [
    ("dog", "강아지", "🐶"),
    ("cat", "고양이", "🐱"),
    ("future", "예비 집사", "🏠"),
]


@login_required
def pet_list(request):
    pets = Pet.objects.filter(user=request.user)
    return render(request, "pets/list.html", {"pets": pets})


def pet_add(request):
    preview_mode = request.GET.get("preview") == "1" or not request.user.is_authenticated

    if request.method == "POST":
        if preview_mode:
            return redirect("/pets/?preview=filled")
        species = request.POST.get("species")
        if species not in ("dog", "cat"):
            return redirect("pet_add")
        Pet.objects.create(
            user=request.user,
            species=species,
            name=request.POST.get("name", "").strip(),
            breed=request.POST.get("breed", "").strip() or None,
            gender=request.POST.get("gender", "male"),
            age_years=int(request.POST.get("age_years", 0) or 0),
            age_months=int(request.POST.get("age_months", 0) or 0),
            weight_kg=request.POST.get("weight_kg") or None,
            neutered={"yes": True, "no": False}.get(request.POST.get("neutered")),
            budget_range="",
        )
        return redirect("pet_list")
    return render(
        request,
        "pets/form.html",
        {
            "species_options": SPECIES_OPTIONS,
            "preview_mode": preview_mode,
        },
    )


@login_required
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
    return render(request, "pets/form.html", {"pet": pet, "species_options": SPECIES_OPTIONS})
