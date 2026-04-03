from ..models import UserProfile
from ..nickname_utils import build_unique_nickname


def get_or_create_profile(user):
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"nickname": build_unique_nickname(user.email.split("@")[0], exclude_user=user)},
    )
    return profile
