from types import SimpleNamespace

import logging

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.db.models import ProtectedError
from django.shortcuts import redirect, render
from django.urls import reverse
from social_core.exceptions import AuthCanceled, AuthConnectionError, AuthException, AuthForbidden, AuthMissingParameter

from .models import UserProfile
from .social_auth import (
    SOCIAL_AUTH_ACCESS_SESSION_KEY,
    SOCIAL_AUTH_REFRESH_SESSION_KEY,
    SOCIAL_AUTH_REMEMBER_SESSION_KEY,
    SocialAuthServiceError,
    build_authorization_url,
    complete_social_login,
)
from .views import issue_user_tokens

User = get_user_model()
logger = logging.getLogger(__name__)


def _get_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user, defaults={"nickname": user.email.split("@")[0]})
    return profile


def home(request):
    if request.user.is_authenticated:
        return redirect("chat")
    return render(request, "chat/index.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("chat")
    return render(request, "users/login.html")


def signup_view(request):
    if request.user.is_authenticated:
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
        preview_profile = SimpleNamespace(nickname="", phone="", marketing_consent=True)
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
        profile.nickname = request.POST.get("nickname", "").strip() or profile.nickname
        profile.phone = request.POST.get("phone", "").strip()
        profile.marketing_consent = request.POST.get("marketing") == "on"
        profile.save(update_fields=["nickname", "phone", "marketing_consent", "updated_at"])
        messages.success(request, "프로필 정보가 저장되었습니다.")
        return redirect("pet_add")

    context = {
        "profile": profile,
        "social_accounts": {account.provider: account for account in request.user.social_accounts.all()},
        "setup_mode": request.GET.get("setup") == "1",
        "profile_preview": False,
    }
    return render(request, "users/profile.html", context)


def profile_withdraw_view(request):
    if request.method != "POST":
        return redirect("profile")

    preview_mode = request.GET.get("preview") == "1" or not request.user.is_authenticated
    if preview_mode:
        return redirect("chat")

    try:
        request.user.delete()
    except ProtectedError:
        messages.error(request, "진행 중이거나 보존이 필요한 주문 데이터가 있어 탈퇴할 수 없습니다.")
        return redirect("profile")

    logout(request)
    messages.success(request, "회원 탈퇴가 완료되었습니다.")
    return redirect("chat")


def social_login_start_view(request, provider):
    remember = request.GET.get("remember") == "on"
    redirect_uri = request.build_absolute_uri(reverse("social-login-callback", kwargs={"provider": provider}))
    next_url = f"{reverse('profile')}?setup=1"

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

    redirect_uri = request.build_absolute_uri(reverse("social-login-callback", kwargs={"provider": provider}))

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
    messages.success(request, "소셜 로그인이 완료되었습니다. 추가 정보를 입력해 주세요.")
    return redirect(f"{reverse('profile')}?setup=1")
