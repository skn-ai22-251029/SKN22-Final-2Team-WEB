import uuid

from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken
from social_django.models import UserSocialAuth

from pets.models import FuturePetProfile

from ..models import SocialAccount, User, UserPreference, UserProfile
from ..nickname_utils import build_unique_nickname


def deactivate_user_and_purge_personal_data(user):
    anonymized_email = f"withdrawn-{user.pk}-{uuid.uuid4().hex[:12]}@deleted.local"

    if hasattr(user, "chat_sessions"):
        user.chat_sessions.all().delete()
    if hasattr(user, "cart"):
        user.cart.delete()
    if hasattr(user, "wishlist"):
        user.wishlist.delete()
    if hasattr(user, "pets"):
        user.pets.all().delete()
    FuturePetProfile.objects.filter(user=user).delete()
    if hasattr(user, "social_accounts"):
        user.social_accounts.all().delete()
    UserSocialAuth.objects.filter(user=user).delete()
    if hasattr(user, "used_products"):
        user.used_products.all().delete()
    if hasattr(user, "userinteraction_set"):
        user.userinteraction_set.all().delete()

    UserPreference.objects.filter(user=user).delete()
    UserProfile.objects.filter(user=user).delete()

    user.email = anonymized_email
    user.is_active = False
    user.set_unusable_password()
    user.save(update_fields=["email", "is_active", "password"])


@transaction.atomic
def get_or_create_social_user(profile):
    social_account = (
        SocialAccount.objects.select_related("user", "user__profile")
        .filter(provider=profile.provider, provider_user_id=profile.provider_user_id)
        .first()
    )
    if social_account:
        sync_social_profile(social_account.user, profile)
        return social_account.user, False

    user = None
    if profile.email:
        user = User.objects.filter(email=profile.email).first()

    if user is None:
        email = profile.email or build_fallback_email(profile.provider, profile.provider_user_id)
        user = User.objects.create_user(email=email)
        UserProfile.objects.create(
            user=user,
            nickname=build_unique_nickname(
                profile.nickname,
                fallback_seed=email.split("@")[0],
            ),
            profile_image_url=profile.profile_image_url,
        )
        is_new_user = True
    else:
        UserProfile.objects.get_or_create(
            user=user,
            defaults={
                "nickname": build_unique_nickname(
                    profile.nickname,
                    fallback_seed=user.email.split("@")[0],
                    exclude_user=user,
                ),
                "profile_image_url": profile.profile_image_url,
            },
        )
        is_new_user = False
        sync_social_profile(user, profile)

    SocialAccount.objects.create(
        user=user,
        provider=profile.provider,
        provider_user_id=profile.provider_user_id,
        email=profile.email or user.email,
        extra_data=profile.extra_data,
    )

    return user, is_new_user


def sync_social_profile(user, profile):
    profile_defaults = {
        "nickname": build_unique_nickname(
            profile.nickname,
            fallback_seed=user.email.split("@")[0],
            exclude_user=user,
        ),
        "profile_image_url": profile.profile_image_url,
    }
    user_profile, _ = UserProfile.objects.get_or_create(user=user, defaults=profile_defaults)

    dirty_fields = []
    next_nickname = build_unique_nickname(
        profile.nickname,
        fallback_seed=user.email.split("@")[0],
        exclude_user=user,
    )
    if next_nickname and user_profile.nickname != next_nickname:
        user_profile.nickname = next_nickname
        dirty_fields.append("nickname")
    if profile.profile_image_url and user_profile.profile_image_url != profile.profile_image_url:
        user_profile.profile_image_url = profile.profile_image_url
        dirty_fields.append("profile_image_url")
    if dirty_fields:
        user_profile.save(update_fields=[*dirty_fields, "updated_at"])


def build_fallback_email(provider: str, provider_user_id: str) -> str:
    return f"{provider}_{provider_user_id}@oauth.local"


def issue_user_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }
