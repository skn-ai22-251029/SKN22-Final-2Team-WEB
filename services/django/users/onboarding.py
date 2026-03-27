from django.urls import reverse

from .models import UserProfile

ONBOARDING_FORCE_PROFILE_SESSION_KEY = "tailtalk_onboarding_force_profile"


def is_profile_complete(user):
    if not getattr(user, "is_authenticated", False):
        return False

    profile = getattr(user, "profile", None)
    if profile is None:
        profile = UserProfile.objects.filter(user=user).first()
    if profile is None:
        return False

    return bool((profile.nickname or "").strip())


def has_completed_pet_onboarding(request):
    if not getattr(request.user, "is_authenticated", False):
        return False

    if request.user.pets.exists():
        return True

    return bool(request.session.get("future_pet_profile"))


def get_onboarding_redirect_url(request):
    if not getattr(request.user, "is_authenticated", False):
        return None

    if request.session.get(ONBOARDING_FORCE_PROFILE_SESSION_KEY):
        return f"{reverse('profile')}?setup=1"

    if not is_profile_complete(request.user):
        return f"{reverse('profile')}?setup=1"

    if not has_completed_pet_onboarding(request):
        return reverse("pet_add")

    return None
