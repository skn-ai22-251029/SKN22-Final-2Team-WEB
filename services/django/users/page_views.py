from types import SimpleNamespace

import logging

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from social_core.exceptions import AuthCanceled, AuthConnectionError, AuthException, AuthForbidden, AuthMissingParameter

from .models import UserProfile
from .nickname_utils import build_unique_nickname, get_nickname_validation_error
from .onboarding import (
    ONBOARDING_FORCE_PROFILE_SESSION_KEY,
    get_onboarding_redirect_url,
    has_completed_pet_onboarding,
)
from .quick_purchase import build_payment_info, split_legacy_address
from .social_auth import (
    SOCIAL_AUTH_ACCESS_SESSION_KEY,
    SOCIAL_AUTH_REFRESH_SESSION_KEY,
    SOCIAL_AUTH_REMEMBER_SESSION_KEY,
    SocialAuthServiceError,
    build_callback_url,
    build_authorization_url,
    complete_social_login,
)
from .views import deactivate_user_and_purge_personal_data, issue_user_tokens

User = get_user_model()
logger = logging.getLogger(__name__)


def _get_profile(user):
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"nickname": build_unique_nickname(user.email.split("@")[0], exclude_user=user)},
    )
    return profile


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
        },
    )


def home(request):
    if request.user.is_authenticated:
        onboarding_redirect_url = get_onboarding_redirect_url(request)
        if onboarding_redirect_url:
            return redirect(onboarding_redirect_url)
        return redirect("chat")
    return render(request, "chat/index.html")


def login_view(request):
    if request.user.is_authenticated:
        onboarding_redirect_url = get_onboarding_redirect_url(request)
        if onboarding_redirect_url:
            return redirect(onboarding_redirect_url)
        return redirect("chat")
    return render(request, "users/login.html")


def signup_view(request):
    if request.user.is_authenticated:
        onboarding_redirect_url = get_onboarding_redirect_url(request)
        if onboarding_redirect_url:
            return redirect(onboarding_redirect_url)
        return redirect("chat")
    return render(request, "users/signup.html")


def logout_view(request):
    request.session.pop(SOCIAL_AUTH_ACCESS_SESSION_KEY, None)
    request.session.pop(SOCIAL_AUTH_REFRESH_SESSION_KEY, None)
    logout(request)
    return redirect("home")


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
            },
        )

    profile = _get_profile(request.user)
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
                profile.save(update_fields=[
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
                ])
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


def profile_withdraw_view(request):
    if request.method != "POST":
        return redirect("profile")

    preview_mode = request.GET.get("preview") == "1" or not request.user.is_authenticated
    if preview_mode:
        return redirect("chat")

    deactivate_user_and_purge_personal_data(request.user)

    logout(request)
    messages.success(request, "회원 탈퇴가 완료되었습니다. 주문 기록을 제외한 사용자 정보가 정리되었습니다.")
    return redirect("home")


def social_login_start_view(request, provider):
    remember = request.GET.get("remember") == "on"
    redirect_uri = build_callback_url(request, "social-login-callback", provider)
    next_url = reverse("chat")

    try:
        authorization_url = build_authorization_url(
            request=request,
            provider=provider,
            redirect_uri=redirect_uri,
            next_url=next_url,
        )
    except SocialAuthServiceError as exc:
        messages.error(request, str(exc))
        return redirect("login")

    request.session[SOCIAL_AUTH_REMEMBER_SESSION_KEY] = remember
    return redirect(authorization_url)


def social_login_callback_view(request, provider):
    if request.GET.get("error"):
        logger.warning("OAuth provider returned error", extra={"provider": provider, "error": request.GET.get("error")})
        messages.error(request, "소셜 로그인 인증이 취소되었거나 실패했습니다.")
        return redirect("login")

    redirect_uri = build_callback_url(request, "social-login-callback", provider)

    try:
        result = complete_social_login(
            request=request,
            provider=provider,
            redirect_uri=redirect_uri,
        )
    except (AuthCanceled, AuthConnectionError, AuthMissingParameter, AuthForbidden, AuthException, SocialAuthServiceError) as exc:
        logger.warning("Social login exchange failed", extra={"provider": provider, "error": str(exc)})
        messages.error(request, str(exc))
        return redirect("login")

    user = result.user
    user.backend = result.backend_path
    login(request, user)
    if not request.session.get(SOCIAL_AUTH_REMEMBER_SESSION_KEY):
        request.session.set_expiry(0)

    tokens = issue_user_tokens(user)
    request.session[SOCIAL_AUTH_ACCESS_SESSION_KEY] = tokens["access"]
    request.session[SOCIAL_AUTH_REFRESH_SESSION_KEY] = tokens["refresh"]
    request.session.pop(SOCIAL_AUTH_REMEMBER_SESSION_KEY, None)
    messages.success(request, "소셜 로그인이 완료되었습니다.")
    if result.is_new_user:
        request.session[ONBOARDING_FORCE_PROFILE_SESSION_KEY] = True
        return redirect(f"{reverse('profile')}?setup=1")
    onboarding_redirect_url = get_onboarding_redirect_url(request)
    if onboarding_redirect_url:
        return redirect(onboarding_redirect_url)
    return redirect("chat")
