from django.core.exceptions import ValidationError

from pets.models import Pet


def get_owned_target_pet(user, pet_id):
    if not pet_id:
        return None

    try:
        return Pet.objects.filter(pet_id=pet_id, user=user).first()
    except (ValidationError, ValueError, TypeError):
        return None
