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
from .onboarding import get_onboarding_redirect_url
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


def _split_profile_address(address):
    if not address:
        return "", ""

    parts = [part.strip() for part in address.split("|", 1)]
    base_address = parts[0] if parts else ""
    detail_address = parts[1] if len(parts) > 1 else ""
    return base_address, detail_address


def _get_profile(user):
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"nickname": build_unique_nickname(user.email.split("@")[0], exclude_user=user)},
    )
    return profile


def _render_profile(request, profile):
    address_main, address_detail = _split_profile_address(profile.address)
    return render(
        request,
        "users/profile.html",
        {
            "profile": profile,
            "profile_address_main": address_main,
            "profile_address_detail": address_detail,
            "profile_payment_method": profile.payment_method or "",
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
    return redirect("login")


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
        address_main = request.POST.get("address_main", "").strip()
        address_detail = request.POST.get("address_detail", "").strip()
        if address_main or address_detail:
            profile.address = " | ".join(part for part in [address_main, address_detail] if part)
        else:
            profile.address = ""
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
                    "phone",
                    "phone_verified",
                    "phone_verified_at",
                    "phone_verification_code",
                    "phone_verification_target",
                    "phone_verification_expires_at",
                    "address",
                    "payment_method",
                    "marketing_consent",
                    "updated_at",
                ])
        except IntegrityError:
            messages.error(request, "이미 사용 중인 닉네임입니다.")
            return _render_profile(request, profile)
        messages.success(request, "프로필 정보가 저장되었습니다.")
        if setup_mode:
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
    return redirect("chat")


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
        return redirect(f"{reverse('profile')}?setup=1")
    onboarding_redirect_url = get_onboarding_redirect_url(request)
    if onboarding_redirect_url:
        return redirect(onboarding_redirect_url)
    return redirect("chat")
