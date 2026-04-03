import random
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from products.models import Product

from ..models import UserPreference, UserUsedProduct
from ..nickname_utils import build_unique_nickname, get_nickname_validation_error
from ..quick_purchase import serialize_quick_purchase_profile, split_legacy_address
from ..selectors.user_selector import get_or_create_profile
from .serializers import (
    normalize_phone,
    serialize_used_product,
    serialize_user_preferences,
    serialize_user_profile,
    validate_phone_or_400,
)


class UserMeView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"user": serialize_user_profile(request.user)})

    def patch(self, request):
        profile = get_or_create_profile(request.user)

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
                if field == "phone" and value != profile.phone:
                    profile.mark_phone_unverified()
                    profile.clear_phone_verification()
                    dirty_fields.extend(
                        [
                            "phone_verified",
                            "phone_verified_at",
                            "phone_verification_code",
                            "phone_verification_target",
                            "phone_verification_expires_at",
                        ]
                    )
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
            marketing_consent = raw_value if isinstance(raw_value, bool) else str(raw_value).lower() in {
                "1",
                "true",
                "on",
                "yes",
            }
            if profile.marketing_consent != marketing_consent:
                profile.marketing_consent = marketing_consent
                dirty_fields.append("marketing_consent")

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
        profile = get_or_create_profile(request.user)
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
            "verification_code": verification_code,
        }
        return Response(response_payload, status=status.HTTP_200_OK)


class UserPhoneVerificationConfirmView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = get_or_create_profile(request.user)
        phone, error_response = validate_phone_or_400(request.data.get("phone"))
        if error_response:
            return error_response

        verification_code = (request.data.get("verification_code") or "").strip()
        if not verification_code:
            return Response({"detail": "verification_code is required."}, status=status.HTTP_400_BAD_REQUEST)

        if (
            profile.phone_verification_target != phone
            or not profile.phone_verification_code
            or profile.phone_verification_code != verification_code
        ):
            return Response({"detail": "인증번호가 올바르지 않습니다."}, status=status.HTTP_400_BAD_REQUEST)

        if not profile.phone_verification_expires_at or profile.phone_verification_expires_at < timezone.now():
            profile.clear_phone_verification()
            profile.save(
                update_fields=[
                    "phone_verification_code",
                    "phone_verification_target",
                    "phone_verification_expires_at",
                    "updated_at",
                ]
            )
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
