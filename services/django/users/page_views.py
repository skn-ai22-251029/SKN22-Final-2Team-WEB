from django.contrib.auth import login, logout
from django.urls import reverse

from .onboarding import ONBOARDING_FORCE_PROFILE_SESSION_KEY, get_onboarding_redirect_url
from .pages import views_auth as auth_page_impl
from .pages import views_profile as profile_page_impl
from .pages import views_vendor as vendor_page_impl
from .social_auth import (
    SOCIAL_AUTH_ACCESS_SESSION_KEY,
    SOCIAL_AUTH_REFRESH_SESSION_KEY,
    SOCIAL_AUTH_REMEMBER_SESSION_KEY,
    SocialAuthServiceError,
    build_authorization_url,
    build_callback_url,
    complete_social_login,
)
from .views import issue_user_tokens

VENDOR_ADMIN_SESSION_KEY = vendor_page_impl.VENDOR_ADMIN_SESSION_KEY
DEMO_VENDOR_ACCOUNTS = vendor_page_impl.DEMO_VENDOR_ACCOUNTS
VENDOR_PRODUCT_SORT_OPTIONS = vendor_page_impl.VENDOR_PRODUCT_SORT_OPTIONS


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
            "social_accounts": {account.provider: account for account in request.user.social_accounts.all()},
            "setup_mode": request.GET.get("setup") == "1",
            "profile_preview": False,
        },
    )


def home(request):
    return auth_page_impl.home(
        request,
        get_onboarding_redirect_url_fn=get_onboarding_redirect_url,
    )


def login_view(request):
    return auth_page_impl.login_view(
        request,
        get_onboarding_redirect_url_fn=get_onboarding_redirect_url,
    )


def signup_view(request):
    return auth_page_impl.signup_view(
        request,
        get_onboarding_redirect_url_fn=get_onboarding_redirect_url,
    )


def logout_view(request):
    return auth_page_impl.logout_view(
        request,
        logout_fn=logout,
        access_session_key=SOCIAL_AUTH_ACCESS_SESSION_KEY,
        refresh_session_key=SOCIAL_AUTH_REFRESH_SESSION_KEY,
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
            },
        )

    profile = _get_profile(request.user)
    if request.method == "POST":
        setup_mode = request.GET.get("setup") == "1"
        profile.nickname = request.POST.get("nickname", "").strip()
        profile.phone = request.POST.get("phone", "").strip()
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
                profile.save(update_fields=["nickname", "phone", "address", "payment_method", "marketing_consent", "updated_at"])
        except IntegrityError:
            messages.error(request, "이미 사용 중인 닉네임입니다.")
            return _render_profile(request, profile)
        messages.success(request, "프로필 정보가 저장되었습니다.")
        if setup_mode:
            return redirect("pet_add")
        return redirect("profile")

    return _render_profile(request, profile)


def profile_withdraw_view(request):
    return profile_page_impl.profile_withdraw_view(
        request,
        logout_fn=logout,
    )


def social_login_start_view(request, provider):
    return auth_page_impl.social_login_start_view(
        request,
        provider,
        build_callback_url_fn=build_callback_url,
        build_authorization_url_fn=build_authorization_url,
        reverse_fn=reverse,
        social_auth_service_error_cls=SocialAuthServiceError,
        remember_session_key=SOCIAL_AUTH_REMEMBER_SESSION_KEY,
    )


def social_login_callback_view(request, provider):
    return auth_page_impl.social_login_callback_view(
        request,
        provider,
        build_callback_url_fn=build_callback_url,
        complete_social_login_fn=complete_social_login,
        issue_user_tokens_fn=issue_user_tokens,
        get_onboarding_redirect_url_fn=get_onboarding_redirect_url,
        login_fn=login,
        access_session_key=SOCIAL_AUTH_ACCESS_SESSION_KEY,
        refresh_session_key=SOCIAL_AUTH_REFRESH_SESSION_KEY,
        remember_session_key=SOCIAL_AUTH_REMEMBER_SESSION_KEY,
        onboarding_force_profile_session_key=ONBOARDING_FORCE_PROFILE_SESSION_KEY,
    )


__all__ = [
    "DEMO_VENDOR_ACCOUNTS",
    "VENDOR_ADMIN_SESSION_KEY",
    "VENDOR_PRODUCT_SORT_OPTIONS",
    "build_authorization_url",
    "complete_social_login",
    "home",
    "login_view",
    "logout_view",
    "profile_view",
    "profile_withdraw_view",
    "signup_view",
    "social_login_callback_view",
    "social_login_start_view",
    "vendor_analytics_view",
    "vendor_dashboard_view",
    "vendor_login_view",
    "vendor_logout_view",
    "vendor_orders_view",
    "vendor_product_create_view",
    "vendor_product_detail_view",
    "vendor_product_edit_view",
    "vendor_products_view",
    "vendor_reviews_view",
]
