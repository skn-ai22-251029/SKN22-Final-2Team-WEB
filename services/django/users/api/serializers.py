from rest_framework import status
from rest_framework.response import Response

from ..models import UserPreference, UserProfile
from ..nickname_utils import build_unique_nickname
from ..quick_purchase import build_delivery_info, build_payment_info
from ..selectors.user_selector import get_or_create_profile


def serialize_user(user):
    profile = get_or_create_profile(user)
    return {
        "id": user.id,
        "email": user.email,
        "nickname": profile.nickname,
        "profile_image_url": profile.profile_image_url,
    }


def serialize_user_profile(user):
    profile = get_or_create_profile(user)
    delivery_info = build_delivery_info(profile)
    payment_info = build_payment_info(profile)
    return {
        "id": user.id,
        "email": user.email,
        "nickname": profile.nickname,
        "recipient_name": delivery_info["recipient_name"],
        "age": profile.age,
        "gender": profile.gender,
        "postal_code": delivery_info["postal_code"],
        "address_main": delivery_info["address_main"],
        "address_detail": delivery_info["address_detail"],
        "address": profile.address,
        "phone": profile.phone,
        "phone_verified": profile.phone_verified,
        "phone_verified_at": profile.phone_verified_at,
        "payment_method": payment_info["payment_summary"],
        "payment_card_provider": payment_info["card_provider"],
        "payment_card_masked_number": payment_info["masked_card_number"],
        "payment_is_default": payment_info["payment_is_default"],
        "payment_token_reference": payment_info["payment_token_reference"],
        "marketing_consent": profile.marketing_consent,
        "profile_image_url": profile.profile_image_url,
    }


def normalize_phone(value):
    return "".join(char for char in str(value or "") if char.isdigit())[:11]


def validate_phone_or_400(phone):
    normalized_phone = normalize_phone(phone)
    if not normalized_phone:
        return None, Response({"detail": "phone is required."}, status=status.HTTP_400_BAD_REQUEST)
    if not 10 <= len(normalized_phone) <= 11:
        return None, Response({"detail": "phone must be 10~11 digits."}, status=status.HTTP_400_BAD_REQUEST)
    return normalized_phone, None


def serialize_user_preferences(user):
    preferences, _ = UserPreference.objects.get_or_create(user=user)
    return {
        "theme": preferences.theme,
        "updated_at": preferences.updated_at,
    }


def serialize_used_product(used_product):
    product = used_product.product
    return {
        "id": str(used_product.id),
        "product_id": product.goods_id,
        "goods_name": product.goods_name,
        "brand_name": product.brand_name,
        "thumbnail_url": product.thumbnail_url,
        "created_at": used_product.created_at,
    }
