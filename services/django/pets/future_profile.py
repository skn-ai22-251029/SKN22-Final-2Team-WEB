from .models import FuturePetProfile


def build_future_pet_profile_dict(profile):
    if not profile:
        return None

    if isinstance(profile, dict):
        return {
            "preferred_species": profile.get("preferred_species", ""),
            "housing_type": profile.get("housing_type", ""),
            "experience_level": profile.get("experience_level", ""),
            "interests": list(profile.get("interests", []) or []),
        }

    return {
        "preferred_species": getattr(profile, "preferred_species", "") or "",
        "housing_type": getattr(profile, "housing_type", "") or "",
        "experience_level": getattr(profile, "experience_level", "") or "",
        "interests": list(getattr(profile, "interests", []) or []),
    }


def get_future_pet_profile_for_request(request):
    if getattr(request.user, "is_authenticated", False):
        profile = FuturePetProfile.objects.filter(user=request.user).first()
        if profile:
            return build_future_pet_profile_dict(profile)

    session_profile = request.session.get("future_pet_profile")
    if session_profile:
        return build_future_pet_profile_dict(session_profile)

    return None
