from django.contrib.auth import get_user_model

from .models import SocialAccount, UserProfile
from .nickname_utils import build_unique_nickname

User = get_user_model()


PROVIDER_NAME_MAP = {
    "google-oauth2": "google",
    "kakao": "kakao",
    "naver": "naver",
}


def build_fallback_email(provider: str, provider_user_id: str) -> str:
    return f"{provider}_{provider_user_id}@oauth.local"


def ensure_email(details, backend, response, uid=None, *args, **kwargs):
    if details.get("email"):
        return None

    provider = PROVIDER_NAME_MAP.get(backend.name, backend.name)
    provider_user_id = uid or backend.get_user_id(details, response)
    fallback_email = build_fallback_email(provider, provider_user_id)
    normalized_details = details.copy()
    normalized_details["email"] = fallback_email
    return {"details": normalized_details}


def associate_active_user_by_email(details, user=None, *args, **kwargs):
    if user is not None:
        return None

    email = (details or {}).get("email")
    if not email:
        return None

    matched_user = User.objects.filter(email__iexact=email, is_active=True).first()
    if matched_user is None:
        return None

    return {"user": matched_user, "is_new": False}


def sync_tailtalk_social_data(backend, user=None, uid=None, response=None, *args, **kwargs):
    if user is None:
        return None

    provider = PROVIDER_NAME_MAP.get(backend.name, backend.name)
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"nickname": build_unique_nickname(user.email.split("@")[0], exclude_user=user)},
    )

    nickname = (
        response.get("name")
        or response.get("nickname")
        or (response.get("properties") or {}).get("nickname")
        or ((response.get("kakao_account") or {}).get("profile") or {}).get("nickname")
        or profile.nickname
    )
    profile_image_url = (
        response.get("picture")
        or response.get("profile_image")
        or (response.get("properties") or {}).get("profile_image")
        or ((response.get("kakao_account") or {}).get("profile") or {}).get("profile_image_url")
        or profile.profile_image_url
    )
    email = (
        response.get("email")
        or (response.get("kakao_account") or {}).get("email")
        or user.email
    )

    dirty_fields = []
    next_nickname = build_unique_nickname(
        nickname,
        fallback_seed=user.email.split("@")[0],
        exclude_user=user,
    )
    if next_nickname and profile.nickname != next_nickname:
        profile.nickname = next_nickname
        dirty_fields.append("nickname")
    if profile_image_url and profile.profile_image_url != profile_image_url:
        profile.profile_image_url = profile_image_url
        dirty_fields.append("profile_image_url")
    if dirty_fields:
        profile.save(update_fields=[*dirty_fields, "updated_at"])

    SocialAccount.objects.update_or_create(
        provider=provider,
        provider_user_id=str(uid),
        defaults={
            "user": user,
            "email": email,
            "extra_data": response or {},
        },
    )
    return None
