from types import SimpleNamespace

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from orders.models import Cart, Wishlist

from ..nickname_utils import get_nickname_validation_error
from ..onboarding import (
    ONBOARDING_FORCE_PROFILE_SESSION_KEY,
    has_completed_pet_onboarding,
)
from ..quick_purchase import build_payment_info, split_legacy_address
from ..selectors.user_selector import get_or_create_profile
from ..services.auth_service import deactivate_user_and_purge_personal_data


def _member_nav_indicator_state(user):
    if not getattr(user, "is_authenticated", False):
        return {
            "member_nav_has_cart_items": False,
            "member_nav_has_wishlist_items": False,
        }

    cart, _ = Cart.objects.get_or_create(user=user)
    wishlist, _ = Wishlist.objects.get_or_create(user=user)
    return {
        "member_nav_has_cart_items": cart.items.exists(),
        "member_nav_has_wishlist_items": wishlist.items.exists(),
    }


def _render_profile(request, profile):
    address_main = (profile.address_main or "").strip()
    address_detail = (profile.address_detail or "").strip()
    if not address_main and not address_detail:
        address_main, address_detail = split_legacy_address(profile.address)
    payment_info = build_payment_info(profile)
    return render(
        request,
        "users/profile.html",
        {
            "profile": profile,
            "profile_zipcode": profile.postal_code or "",
            "profile_address_main": address_main,
            "profile_address_detail": address_detail,
            "profile_payment_method": payment_info["payment_summary"],
            "profile_payment_card_provider": payment_info["card_provider"],
            "profile_payment_card_masked_number": payment_info["masked_card_number"],
            "profile_payment_token_reference": payment_info["payment_token_reference"],
            "profile_phone_verified": profile.phone_verified,
            "social_accounts": {account.provider: account for account in request.user.social_accounts.all()},
            "setup_mode": request.GET.get("setup") == "1",
            "profile_preview": False,
            "juso_confm_key": settings.JUSO_CONFM_KEY,
            **_member_nav_indicator_state(request.user),
        },
    )


def profile_view(request):
    preview_mode = request.GET.get("preview") == "1" or not request.user.is_authenticated

    if preview_mode:
        preview_profile = SimpleNamespace(nickname="", phone="", marketing_consent=False)
        preview_social_accounts = {
            "kakao": SimpleNamespace(email="tailtalk_user@kakao.com"),
        }
        if request.method == "POST":
            return redirect("pet_add")
        return render(
            request,
            "users/profile.html",
            {
                "profile": preview_profile,
                "profile_preview": True,
                "social_accounts": preview_social_accounts,
                "setup_mode": request.GET.get("setup") == "1",
                "juso_confm_key": settings.JUSO_CONFM_KEY,
                **_member_nav_indicator_state(request.user),
            },
        )

    profile = get_or_create_profile(request.user)
    if request.method == "POST":
        setup_mode = request.GET.get("setup") == "1"
        profile.nickname = request.POST.get("nickname", "").strip()
        profile.recipient_name = profile.nickname
        submitted_phone = "".join(char for char in request.POST.get("phone", "") if char.isdigit())[:11]
        if submitted_phone and not 10 <= len(submitted_phone) <= 11:
            messages.error(request, "연락처는 10~11자리 숫자만 입력해 주세요.")
            return _render_profile(request, profile)
        if submitted_phone != (profile.phone or "") and submitted_phone:
            messages.error(request, "연락처 인증을 완료해 주세요.")
            return _render_profile(request, profile)
        if submitted_phone and not profile.phone_verified:
            messages.error(request, "연락처 인증을 완료해 주세요.")
            return _render_profile(request, profile)
        if not submitted_phone:
            profile.phone = ""
            profile.phone_verified = False
            profile.phone_verified_at = None
            profile.clear_phone_verification()
        else:
            profile.phone = submitted_phone
        postal_code = request.POST.get("zipcode", "").strip()
        address_main = request.POST.get("address_main", "").strip()
        address_detail = request.POST.get("address_detail", "").strip()
        profile.postal_code = postal_code
        profile.address_main = address_main
        profile.address_detail = address_detail
        if address_main or address_detail:
            profile.address = " | ".join(part for part in [address_main, address_detail] if part)
        else:
            profile.address = ""
        profile.payment_card_provider = request.POST.get("payment_card_provider", "").strip()
        profile.payment_card_masked_number = request.POST.get("payment_card_masked_number", "").strip()
        profile.payment_token_reference = request.POST.get("payment_token_reference", "").strip()
        profile.payment_is_default = True
        profile.payment_method = request.POST.get("payment_method", "").strip()
        profile.marketing_consent = request.POST.get("marketing") == "on"
        nickname_error = get_nickname_validation_error(profile.nickname, exclude_user=request.user)
        if nickname_error:
            messages.error(request, nickname_error)
            return _render_profile(request, profile)
        try:
            with transaction.atomic():
                profile.save(
                    update_fields=[
                        "nickname",
                        "recipient_name",
                        "phone",
                        "phone_verified",
                        "phone_verified_at",
                        "phone_verification_code",
                        "phone_verification_target",
                        "phone_verification_expires_at",
                        "postal_code",
                        "address_main",
                        "address_detail",
                        "address",
                        "payment_card_provider",
                        "payment_card_masked_number",
                        "payment_is_default",
                        "payment_token_reference",
                        "payment_method",
                        "marketing_consent",
                        "updated_at",
                    ]
                )
        except IntegrityError:
            messages.error(request, "이미 사용 중인 닉네임입니다.")
            return _render_profile(request, profile)
        messages.success(request, "프로필 정보가 저장되었습니다.")
        if setup_mode:
            request.session.pop(ONBOARDING_FORCE_PROFILE_SESSION_KEY, None)
            if has_completed_pet_onboarding(request):
                return redirect("chat")
            return redirect("pet_add")
        return redirect("chat")

    return _render_profile(request, profile)


def profile_withdraw_view(request, *, logout_fn=logout):
    if request.method != "POST":
        return redirect("profile")

    preview_mode = request.GET.get("preview") == "1" or not request.user.is_authenticated
    if preview_mode:
        return redirect("chat")

    deactivate_user_and_purge_personal_data(request.user)

    logout_fn(request)
    messages.success(request, "회원 탈퇴가 완료되었습니다. 주문 기록을 제외한 사용자 정보가 정리되었습니다.")
    return redirect("home")
