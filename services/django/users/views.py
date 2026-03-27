import os
import random
import uuid
from datetime import timedelta
from pathlib import Path

import boto3
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from social_core.exceptions import AuthCanceled, AuthConnectionError, AuthException, AuthForbidden, AuthMissingParameter

from products.models import Product

from .models import SocialAccount, User, UserPreference, UserProfile, UserUsedProduct
from .nickname_utils import (
    build_unique_nickname,
    get_nickname_duplicate_error,
    get_nickname_policy_error,
    get_nickname_validation_error,
)
from .social_auth import (
    SOCIAL_AUTH_ACCESS_SESSION_KEY,
    SOCIAL_AUTH_REFRESH_SESSION_KEY,
    SOCIAL_AUTH_REMEMBER_SESSION_KEY,
    SocialAuthServiceError,
    build_callback_url,
    build_authorization_url,
    complete_social_login,
)
from .quick_purchase import build_delivery_info, build_payment_info, serialize_quick_purchase_profile, split_legacy_address


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
    if hasattr(user, "social_accounts"):
        user.social_accounts.all().delete()
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


def serialize_user(user):
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"nickname": build_unique_nickname(user.email.split("@")[0], exclude_user=user)},
    )
    return {
        "id": user.id,
        "email": user.email,
        "nickname": profile.nickname,
        "profile_image_url": profile.profile_image_url,
    }


def serialize_user_profile(user):
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"nickname": build_unique_nickname(user.email.split("@")[0], exclude_user=user)},
    )
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


# Profile image upload is intentionally disabled for now.
# Keep the helper here so the previous local/S3 flow can be restored quickly.
# def upload_profile_image(file_obj):
#     extension = os.path.splitext(file_obj.name)[1].lower() or ".bin"
#     content_type = getattr(file_obj, "content_type", None) or "application/octet-stream"
#     key = f"profile-images/{uuid.uuid4()}{extension}"
#
#     if not settings.AWS_S3_BUCKET_NAME:
#         media_root = Path(settings.MEDIA_ROOT)
#         destination = media_root / key
#         destination.parent.mkdir(parents=True, exist_ok=True)
#
#         with destination.open("wb+") as output:
#             for chunk in file_obj.chunks():
#                 output.write(chunk)
#
#         return f"{settings.MEDIA_URL.rstrip('/')}/{key}"
#
#     client_kwargs = {}
#     if settings.AWS_S3_REGION_NAME:
#         client_kwargs["region_name"] = settings.AWS_S3_REGION_NAME
#     if settings.AWS_S3_ENDPOINT_URL:
#         client_kwargs["endpoint_url"] = settings.AWS_S3_ENDPOINT_URL
#
#     s3 = boto3.client("s3", **client_kwargs)
#     s3.upload_fileobj(
#         file_obj,
#         settings.AWS_S3_BUCKET_NAME,
#         key,
#         ExtraArgs={"ContentType": content_type},
#     )
#
#     if settings.AWS_S3_CUSTOM_DOMAIN:
#         return f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/{key}"
#
#     if settings.AWS_S3_ENDPOINT_URL:
#         return f"{settings.AWS_S3_ENDPOINT_URL.rstrip('/')}/{settings.AWS_S3_BUCKET_NAME}/{key}"
#
#     region = settings.AWS_S3_REGION_NAME or "us-east-1"
#     return f"https://{settings.AWS_S3_BUCKET_NAME}.s3.{region}.amazonaws.com/{key}"


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip()
        password = request.data.get("password", "")
        nickname = request.data.get("nickname", "").strip()

        if not email or not password:
            return Response({"detail": "email and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({"detail": "이미 사용 중인 이메일입니다."}, status=status.HTTP_400_BAD_REQUEST)

        if nickname:
            nickname_error = get_nickname_validation_error(nickname)
            if nickname_error:
                return Response({"detail": nickname_error}, status=status.HTTP_400_BAD_REQUEST)
            profile_nickname = nickname
        else:
            profile_nickname = build_unique_nickname(email.split("@")[0])

        try:
            with transaction.atomic():
                user = User.objects.create_user(email=email, password=password)
                UserProfile.objects.create(user=user, nickname=profile_nickname)
        except IntegrityError:
            return Response({"detail": "이미 사용 중인 닉네임입니다."}, status=status.HTTP_400_BAD_REQUEST)

        tokens = issue_user_tokens(user)
        return Response(
            {
                **tokens,
                "user": serialize_user(user),
            },
            status=status.HTTP_201_CREATED,
        )


class AuthLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip()
        password = request.data.get("password", "")

        if not email or not password:
            return Response({"detail": "email and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response({"detail": "이메일 또는 비밀번호가 올바르지 않습니다."}, status=status.HTTP_401_UNAUTHORIZED)

        tokens = issue_user_tokens(user)
        return Response(
            {
                **tokens,
                "user": serialize_user(user),
            }
        )


class AuthLogoutView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "refresh is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response({"detail": "유효하지 않은 refresh token 입니다."}, status=status.HTTP_400_BAD_REQUEST)

        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AuthWithdrawView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def delete(self, request):
        refresh_token = request.data.get("refresh")
        user = request.user

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                return Response({"detail": "유효하지 않은 refresh token 입니다."}, status=status.HTTP_400_BAD_REQUEST)

        deactivate_user_and_purge_personal_data(user)

        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class NicknameAvailabilityView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        nickname = request.query_params.get("nickname", "").strip()
        if not nickname:
            return Response({"detail": "nickname is required."}, status=status.HTTP_400_BAD_REQUEST)

        exclude_user = request.user if request.user.is_authenticated else None
        policy_error = get_nickname_policy_error(nickname)
        duplicate_error = None if policy_error else get_nickname_duplicate_error(nickname, exclude_user=exclude_user)
        detail = policy_error or duplicate_error or "사용 가능한 닉네임입니다."

        return Response(
            {
                "nickname": nickname,
                "valid": policy_error is None,
                "available": policy_error is None and duplicate_error is None,
                "detail": detail,
            }
        )


class UserMeView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"user": serialize_user_profile(request.user)})

    def patch(self, request):
        profile, _ = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={"nickname": build_unique_nickname(request.user.email.split("@")[0], exclude_user=request.user)},
        )

        if "nickname" in request.data:
            nickname = (request.data.get("nickname") or "").strip()
            nickname_error = get_nickname_validation_error(nickname, exclude_user=request.user)
            if nickname_error:
                return Response({"detail": nickname_error}, status=status.HTTP_400_BAD_REQUEST)

        dirty_fields = []
        for field in [
            "nickname",
            "recipient_name",
            "age",
            "gender",
            "postal_code",
            "address_main",
            "address_detail",
            "address",
            "phone",
            "payment_method",
            "payment_card_provider",
            "payment_card_masked_number",
            "payment_token_reference",
        ]:
            if field not in request.data:
                continue
            value = request.data.get(field)
            if field == "nickname":
                value = (value or "").strip()
            elif field in {
                "recipient_name",
                "postal_code",
                "address_main",
                "address_detail",
                "address",
                "phone",
                "payment_method",
                "payment_card_provider",
                "payment_card_masked_number",
                "payment_token_reference",
            }:
                value = (value or "").strip() or None
            elif value == "":
                value = None if field != "nickname" else profile.nickname
            if field == "age" and value is not None:
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    return Response({"detail": "age must be an integer."}, status=status.HTTP_400_BAD_REQUEST)
            if field == "phone" and value is not None:
                value = normalize_phone(value)
                if value and not 10 <= len(value) <= 11:
                    return Response({"detail": "phone must be 10~11 digits."}, status=status.HTTP_400_BAD_REQUEST)
            if getattr(profile, field) != value:
                if field == "phone":
                    if value != profile.phone:
                        profile.mark_phone_unverified()
                        profile.clear_phone_verification()
                        dirty_fields.extend(["phone_verified", "phone_verified_at", "phone_verification_code", "phone_verification_target", "phone_verification_expires_at"])
                setattr(profile, field, value)
                dirty_fields.append(field)

        if "nickname" in request.data and "recipient_name" not in request.data:
            next_recipient_name = (profile.nickname or "").strip() or None
            if profile.recipient_name != next_recipient_name:
                profile.recipient_name = next_recipient_name
                dirty_fields.append("recipient_name")

        if any(field in request.data for field in {"postal_code", "address_main", "address_detail", "address"}):
            address_main = (profile.address_main or "").strip()
            address_detail = (profile.address_detail or "").strip()
            if not address_main and not address_detail and profile.address:
                address_main, address_detail = split_legacy_address(profile.address)
                profile.address_main = address_main or None
                profile.address_detail = address_detail or None
                dirty_fields.extend(["address_main", "address_detail"])
            combined_address = " | ".join(part for part in [address_main, address_detail] if part) or None
            if profile.address != combined_address:
                profile.address = combined_address
                dirty_fields.append("address")

        if any(field in request.data for field in {"payment_method", "payment_card_provider", "payment_card_masked_number"}):
            provider = (profile.payment_card_provider or "").strip()
            masked_number = (profile.payment_card_masked_number or "").strip()
            payment_summary = (profile.payment_method or "").strip()
            if not payment_summary and provider and masked_number:
                payment_summary = f"{provider} / {masked_number}"
            if profile.payment_method != (payment_summary or None):
                profile.payment_method = payment_summary or None
                dirty_fields.append("payment_method")

        if "marketing_consent" in request.data:
            raw_value = request.data.get("marketing_consent")
            marketing_consent = raw_value if isinstance(raw_value, bool) else str(raw_value).lower() in {"1", "true", "on", "yes"}
            if profile.marketing_consent != marketing_consent:
                profile.marketing_consent = marketing_consent
                dirty_fields.append("marketing_consent")

        # Profile image upload is intentionally disabled for now.
        # profile_image = request.FILES.get("profile_image")
        # if profile_image is not None:
        #     try:
        #         profile.profile_image_url = upload_profile_image(profile_image)
        #     except ValueError as exc:
        #         return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        #     dirty_fields.append("profile_image_url")

        if dirty_fields:
            try:
                with transaction.atomic():
                    profile.save(update_fields=[*dirty_fields, "updated_at"])
            except IntegrityError:
                return Response({"detail": "이미 사용 중인 닉네임입니다."}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"user": serialize_user_profile(request.user)})


class UserQuickPurchaseDefaultsView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"quick_purchase": serialize_quick_purchase_profile(request.user)})


class UserPhoneVerificationRequestView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile, _ = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={"nickname": build_unique_nickname(request.user.email.split("@")[0], exclude_user=request.user)},
        )
        phone, error_response = validate_phone_or_400(request.data.get("phone"))
        if error_response:
            return error_response

        verification_code = f"{random.randint(0, 999999):06d}"
        profile.phone_verification_target = phone
        profile.phone_verification_code = verification_code
        profile.phone_verification_expires_at = timezone.now() + timedelta(minutes=5)
        profile.phone_verified = False
        profile.phone_verified_at = None
        profile.save(
            update_fields=[
                "phone_verification_target",
                "phone_verification_code",
                "phone_verification_expires_at",
                "phone_verified",
                "phone_verified_at",
                "updated_at",
            ]
        )

        response_payload = {
            "detail": "인증번호를 전송했습니다.",
            "phone": phone,
            "expires_in_seconds": 300,
        }
        if settings.DEBUG:
            response_payload["verification_code"] = verification_code
        return Response(response_payload, status=status.HTTP_200_OK)


class UserPhoneVerificationConfirmView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile, _ = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={"nickname": build_unique_nickname(request.user.email.split("@")[0], exclude_user=request.user)},
        )
        phone, error_response = validate_phone_or_400(request.data.get("phone"))
        if error_response:
            return error_response

        verification_code = (request.data.get("verification_code") or "").strip()
        if not verification_code:
            return Response({"detail": "verification_code is required."}, status=status.HTTP_400_BAD_REQUEST)

        if (
            profile.phone_verification_target != phone or
            not profile.phone_verification_code or
            profile.phone_verification_code != verification_code
        ):
            return Response({"detail": "인증번호가 올바르지 않습니다."}, status=status.HTTP_400_BAD_REQUEST)

        if not profile.phone_verification_expires_at or profile.phone_verification_expires_at < timezone.now():
            profile.clear_phone_verification()
            profile.save(update_fields=["phone_verification_code", "phone_verification_target", "phone_verification_expires_at", "updated_at"])
            return Response({"detail": "인증번호가 만료되었습니다. 다시 요청해 주세요."}, status=status.HTTP_400_BAD_REQUEST)

        profile.phone = phone
        profile.phone_verified = True
        profile.phone_verified_at = timezone.now()
        profile.clear_phone_verification()
        profile.save(
            update_fields=[
                "phone",
                "phone_verified",
                "phone_verified_at",
                "phone_verification_code",
                "phone_verification_target",
                "phone_verification_expires_at",
                "updated_at",
            ]
        )
        return Response({"detail": "연락처 인증이 완료되었습니다.", "user": serialize_user_profile(request.user)})


class UserMePreferenceView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"preferences": serialize_user_preferences(request.user)})

    def patch(self, request):
        preferences, _ = UserPreference.objects.get_or_create(user=request.user)
        theme = request.data.get("theme")
        if theme not in {choice for choice, _ in UserPreference.THEME_CHOICES}:
            return Response({"detail": "theme must be one of: system, light, dark."}, status=status.HTTP_400_BAD_REQUEST)

        if preferences.theme != theme:
            preferences.theme = theme
            preferences.save(update_fields=["theme", "updated_at"])

        return Response({"preferences": serialize_user_preferences(request.user)})


class UserMeUsedProductView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get("product_id")
        if not product_id:
            return Response({"detail": "product_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        product = Product.objects.filter(goods_id=product_id).first()
        if product is None:
            return Response({"detail": "product not found."}, status=status.HTTP_404_NOT_FOUND)

        used_product, created = UserUsedProduct.objects.get_or_create(user=request.user, product=product)
        return Response(
            {"used_product": serialize_used_product(used_product)},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request):
        product_id = request.data.get("product_id")
        if not product_id:
            return Response({"detail": "product_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        deleted, _ = UserUsedProduct.objects.filter(user=request.user, product_id=product_id).delete()
        if not deleted:
            return Response({"detail": "used product not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_204_NO_CONTENT)
