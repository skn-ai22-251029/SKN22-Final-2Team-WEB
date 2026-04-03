import logging

from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.urls import reverse
from social_core.exceptions import AuthCanceled, AuthConnectionError, AuthException, AuthForbidden, AuthMissingParameter

from ..onboarding import ONBOARDING_FORCE_PROFILE_SESSION_KEY, get_onboarding_redirect_url
from ..services.auth_service import issue_user_tokens
from ..social_auth import (
    SOCIAL_AUTH_ACCESS_SESSION_KEY,
    SOCIAL_AUTH_REFRESH_SESSION_KEY,
    SOCIAL_AUTH_REMEMBER_SESSION_KEY,
    SocialAuthServiceError,
    build_authorization_url,
    build_callback_url,
    complete_social_login,
)

logger = logging.getLogger(__name__)


def home(request, *, get_onboarding_redirect_url_fn=get_onboarding_redirect_url):
    if request.user.is_authenticated:
        onboarding_redirect_url = get_onboarding_redirect_url_fn(request)
        if onboarding_redirect_url:
            return redirect(onboarding_redirect_url)
        return redirect("chat")
    return render(request, "chat/index.html")


def login_view(request, *, get_onboarding_redirect_url_fn=get_onboarding_redirect_url):
    if request.user.is_authenticated:
        onboarding_redirect_url = get_onboarding_redirect_url_fn(request)
        if onboarding_redirect_url:
            return redirect(onboarding_redirect_url)
        return redirect("chat")
    return render(request, "users/login.html")


def signup_view(request, *, get_onboarding_redirect_url_fn=get_onboarding_redirect_url):
    if request.user.is_authenticated:
        onboarding_redirect_url = get_onboarding_redirect_url_fn(request)
        if onboarding_redirect_url:
            return redirect(onboarding_redirect_url)
        return redirect("chat")
    return render(request, "users/signup.html")


def logout_view(
    request,
    *,
    logout_fn=logout,
    access_session_key=SOCIAL_AUTH_ACCESS_SESSION_KEY,
    refresh_session_key=SOCIAL_AUTH_REFRESH_SESSION_KEY,
):
    request.session.pop(access_session_key, None)
    request.session.pop(refresh_session_key, None)
    logout_fn(request)
    return redirect("home")


def social_login_start_view(
    request,
    provider,
    *,
    build_callback_url_fn=build_callback_url,
    build_authorization_url_fn=build_authorization_url,
    reverse_fn=reverse,
    social_auth_service_error_cls=SocialAuthServiceError,
    remember_session_key=SOCIAL_AUTH_REMEMBER_SESSION_KEY,
):
    remember = request.GET.get("remember") == "on"
    redirect_uri = build_callback_url_fn(request, "social-login-callback", provider)
    next_url = reverse_fn("chat")

    try:
        authorization_url = build_authorization_url_fn(
            request=request,
            provider=provider,
            redirect_uri=redirect_uri,
            next_url=next_url,
        )
    except social_auth_service_error_cls as exc:
        messages.error(request, str(exc))
        return redirect("login")

    request.session[remember_session_key] = remember
    return redirect(authorization_url)


def social_login_callback_view(
    request,
    provider,
    *,
    build_callback_url_fn=build_callback_url,
    complete_social_login_fn=complete_social_login,
    issue_user_tokens_fn=issue_user_tokens,
    get_onboarding_redirect_url_fn=get_onboarding_redirect_url,
    login_fn=login,
    access_session_key=SOCIAL_AUTH_ACCESS_SESSION_KEY,
    refresh_session_key=SOCIAL_AUTH_REFRESH_SESSION_KEY,
    remember_session_key=SOCIAL_AUTH_REMEMBER_SESSION_KEY,
    onboarding_force_profile_session_key=ONBOARDING_FORCE_PROFILE_SESSION_KEY,
):
    if request.GET.get("error"):
        logger.warning("OAuth provider returned error", extra={"provider": provider, "error": request.GET.get("error")})
        messages.error(request, "소셜 로그인 인증이 취소되었거나 실패했습니다.")
        return redirect("login")

    redirect_uri = build_callback_url_fn(request, "social-login-callback", provider)

    try:
        result = complete_social_login_fn(
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
    login_fn(request, user)
    if not request.session.get(remember_session_key):
        request.session.set_expiry(0)

    tokens = issue_user_tokens_fn(user)
    request.session[access_session_key] = tokens["access"]
    request.session[refresh_session_key] = tokens["refresh"]
    request.session.pop(remember_session_key, None)
    messages.success(request, "소셜 로그인이 완료되었습니다.")
    if result.is_new_user:
        request.session[onboarding_force_profile_session_key] = True
        return redirect(f"{reverse('profile')}?setup=1")
    onboarding_redirect_url = get_onboarding_redirect_url_fn(request)
    if onboarding_redirect_url:
        return redirect(onboarding_redirect_url)
    return redirect("chat")
