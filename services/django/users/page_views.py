import logging

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
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

    error = None
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        remember_me = request.POST.get("remember_me") == "on"
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            if not remember_me:
                request.session.set_expiry(0)
            return redirect(request.GET.get("next", "chat"))
        error = "이메일 또는 비밀번호가 올바르지 않습니다."

    return render(request, "users/login.html", {"error": error})


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("chat")

    error = None
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        nickname = request.POST.get("nickname", "").strip()
        if User.objects.filter(email=email).exists():
            error = "이미 사용 중인 이메일입니다."
        elif password != request.POST.get("password2", ""):
            error = "비밀번호가 일치하지 않습니다."
        else:
            user = User.objects.create_user(email=email, password=password)
            UserProfile.objects.create(user=user, nickname=nickname or email.split("@")[0])
            login(request, user)
            return redirect("profile")

    return render(request, "users/signup.html", {"error": error})


def logout_view(request):
    request.session.pop(SOCIAL_AUTH_ACCESS_SESSION_KEY, None)
    request.session.pop(SOCIAL_AUTH_REFRESH_SESSION_KEY, None)
    logout(request)
    return redirect("login")


@login_required
def profile_view(request):
    profile = _get_profile(request.user)

    if request.method == "POST":
        profile.nickname = request.POST.get("nickname", "").strip() or profile.nickname
        profile.phone = request.POST.get("phone", "").strip()
        profile.marketing_consent = request.POST.get("marketing") == "on"
        profile.save(update_fields=["nickname", "phone", "marketing_consent", "updated_at"])
        messages.success(request, "프로필 정보가 저장되었습니다.")
        return redirect("chat")

    context = {
        "social_accounts": {account.provider: account for account in request.user.social_accounts.all()},
        "setup_mode": request.GET.get("setup") == "1",
    }
    return render(request, "users/profile.html", context)


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
