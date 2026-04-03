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

vendor_login_view = vendor_page_impl.vendor_login_view
vendor_logout_view = vendor_page_impl.vendor_logout_view
vendor_dashboard_view = vendor_page_impl.vendor_dashboard_view
vendor_products_view = vendor_page_impl.vendor_products_view
vendor_analytics_view = vendor_page_impl.vendor_analytics_view
vendor_product_create_view = vendor_page_impl.vendor_product_create_view
vendor_product_edit_view = vendor_page_impl.vendor_product_edit_view
vendor_orders_view = vendor_page_impl.vendor_orders_view
vendor_reviews_view = vendor_page_impl.vendor_reviews_view


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
    return profile_page_impl.profile_view(request)


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
    "vendor_product_edit_view",
    "vendor_products_view",
    "vendor_reviews_view",
]
