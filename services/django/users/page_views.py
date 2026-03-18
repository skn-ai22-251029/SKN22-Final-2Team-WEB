import logging

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from .models import UserProfile
from .oauth import OAuthProviderClient, SocialAuthError
from .views import get_or_create_social_user

User = get_user_model()
logger = logging.getLogger(__name__)
SOCIAL_STATE_SESSION_KEY = "tailtalk_social_oauth_state"
SOCIAL_REMEMBER_SESSION_KEY = "tailtalk_social_oauth_remember"


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

    try:
        client = OAuthProviderClient(provider)
        provider_data = client.build_authorization_url(redirect_uri=redirect_uri)
    except SocialAuthError as exc:
        messages.error(request, str(exc))
        return redirect("login")

    request.session[SOCIAL_STATE_SESSION_KEY] = {
        "provider": provider,
        "state": provider_data["state"],
    }
    request.session[SOCIAL_REMEMBER_SESSION_KEY] = remember
    return redirect(provider_data["authorization_url"])


def social_login_callback_view(request, provider):
    if request.GET.get("error"):
        logger.warning("OAuth provider returned error", extra={"provider": provider, "error": request.GET.get("error")})
        messages.error(request, "소셜 로그인 인증이 취소되었거나 실패했습니다.")
        return redirect("login")

    code = request.GET.get("code")
    state = request.GET.get("state")
    redirect_uri = request.build_absolute_uri(reverse("social-login-callback", kwargs={"provider": provider}))
    oauth_state = request.session.get(SOCIAL_STATE_SESSION_KEY, {})

    if not code:
        logger.warning("OAuth callback missing code", extra={"provider": provider})
        messages.error(request, "인가 코드가 없어 로그인을 완료할 수 없습니다.")
        return redirect("login")

    if oauth_state.get("provider") != provider:
        logger.warning(
            "OAuth callback provider mismatch",
            extra={"provider": provider, "session_provider": oauth_state.get("provider")},
        )
        messages.error(request, "소셜 로그인 상태 정보가 올바르지 않습니다.")
        return redirect("login")

    if provider == "naver" and oauth_state.get("state") != state:
        logger.warning("Naver OAuth state mismatch", extra={"provider": provider})
        messages.error(request, "네이버 로그인 state 검증에 실패했습니다.")
        return redirect("login")

    try:
        profile = OAuthProviderClient(provider).exchange_code(
            code=code,
            redirect_uri=redirect_uri,
            state=state,
        )
        user, _ = get_or_create_social_user(profile)
    except SocialAuthError as exc:
        logger.warning("Social login exchange failed", extra={"provider": provider, "error": str(exc)})
        messages.error(request, str(exc))
        return redirect("login")

    login(request, user)
    if not request.session.get(SOCIAL_REMEMBER_SESSION_KEY):
        request.session.set_expiry(0)

    request.session.pop(SOCIAL_STATE_SESSION_KEY, None)
    request.session.pop(SOCIAL_REMEMBER_SESSION_KEY, None)
    messages.success(request, "소셜 로그인이 완료되었습니다. 추가 정보를 입력해 주세요.")
    return redirect(f"{reverse('profile')}?setup=1")
