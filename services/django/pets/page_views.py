from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import Pet


@login_required
def pet_list(request):
    pets = Pet.objects.filter(user=request.user)
    return render(request, "pets/list.html", {"pets": pets})


@login_required
def pet_add(request):
    return render(request, "pets/form.html")


@login_required
def pet_edit(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id, user=request.user)
    return render(request, "pets/form.html", {"pet": pet})
