import os
import uuid
from pathlib import Path

import boto3
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.db.models import ProtectedError
from django.db import transaction
from django.urls import reverse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from social_core.exceptions import AuthCanceled, AuthConnectionError, AuthException, AuthForbidden, AuthMissingParameter

from products.models import Product

from .models import SocialAccount, User, UserPreference, UserProfile, UserUsedProduct
from .social_auth import (
    SOCIAL_AUTH_ACCESS_SESSION_KEY,
    SOCIAL_AUTH_REFRESH_SESSION_KEY,
    SOCIAL_AUTH_REMEMBER_SESSION_KEY,
    SocialAuthServiceError,
    build_callback_url,
    build_authorization_url,
    complete_social_login,
)


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
            nickname=profile.nickname,
            profile_image_url=profile.profile_image_url,
        )
        is_new_user = True
    else:
        UserProfile.objects.get_or_create(
            user=user,
            defaults={
                "nickname": profile.nickname,
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
        "nickname": profile.nickname,
        "profile_image_url": profile.profile_image_url,
    }
    user_profile, _ = UserProfile.objects.get_or_create(user=user, defaults=profile_defaults)

    dirty_fields = []
    if profile.nickname and user_profile.nickname != profile.nickname:
        user_profile.nickname = profile.nickname
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
    profile, _ = UserProfile.objects.get_or_create(user=user, defaults={"nickname": user.email.split("@")[0]})
    return {
        "id": user.id,
        "email": user.email,
        "nickname": profile.nickname,
        "profile_image_url": profile.profile_image_url,
    }


def serialize_user_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user, defaults={"nickname": user.email.split("@")[0]})
    return {
        "id": user.id,
        "email": user.email,
        "nickname": profile.nickname,
        "age": profile.age,
        "gender": profile.gender,
        "address": profile.address,
        "phone": profile.phone,
        "marketing_consent": profile.marketing_consent,
        "profile_image_url": profile.profile_image_url,
    }


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

        user = User.objects.create_user(email=email, password=password)
        UserProfile.objects.create(user=user, nickname=nickname or email.split("@")[0])

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

        try:
            user.delete()
        except ProtectedError:
            return Response(
                {"detail": "진행 중이거나 보존이 필요한 주문 데이터가 있어 탈퇴할 수 없습니다."},
                status=status.HTTP_409_CONFLICT,
            )

        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"user": serialize_user_profile(request.user)})

    def patch(self, request):
        profile, _ = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={"nickname": request.user.email.split("@")[0]},
        )

        dirty_fields = []
        for field in ["nickname", "age", "gender", "address", "phone"]:
            if field not in request.data:
                continue
            value = request.data.get(field)
            if value == "":
                value = None if field != "nickname" else profile.nickname
            if field == "age" and value is not None:
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    return Response({"detail": "age must be an integer."}, status=status.HTTP_400_BAD_REQUEST)
            if getattr(profile, field) != value:
                setattr(profile, field, value)
                dirty_fields.append(field)

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
            profile.save(update_fields=[*dirty_fields, "updated_at"])

        return Response({"user": serialize_user_profile(request.user)})


class UserMePreferenceView(APIView):
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
