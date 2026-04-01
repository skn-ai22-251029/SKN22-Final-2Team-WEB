from dataclasses import dataclass
from urllib.parse import urlparse

from django.conf import settings
from django.http import HttpResponseBase
from django.urls import reverse
from social_django.utils import load_backend, load_strategy
from social_core.exceptions import MissingBackend


SOCIAL_AUTH_REMEMBER_SESSION_KEY = "tailtalk_social_oauth_remember"
SOCIAL_AUTH_ACCESS_SESSION_KEY = "tailtalk_api_access_token"
SOCIAL_AUTH_REFRESH_SESSION_KEY = "tailtalk_api_refresh_token"

PROVIDER_BACKEND_NAMES = {
    "google": "google-oauth2",
    "kakao": "kakao",
    "naver": "naver",
}

BACKEND_PROVIDER_NAMES = {backend: provider for provider, backend in PROVIDER_BACKEND_NAMES.items()}


class SocialAuthServiceError(Exception):
    pass


@dataclass
class SocialLoginResult:
    user: object
    backend_path: str
    provider: str
    is_new_user: bool


def get_backend_name(provider: str) -> str:
    try:
        return PROVIDER_BACKEND_NAMES[provider]
    except KeyError as exc:
        raise SocialAuthServiceError(f"Unsupported provider: {provider}") from exc


def get_provider_name(backend_name: str) -> str:
    return BACKEND_PROVIDER_NAMES.get(backend_name, backend_name)


def build_callback_url(request, route_name: str, provider: str) -> str:
    path = reverse(route_name, kwargs={"provider": provider})
    request_absolute_uri = request.build_absolute_uri(path)
    if not settings.APP_BASE_URL:
        return request_absolute_uri

    current_host = request.get_host().split(":", 1)[0]
    app_base_host = urlparse(settings.APP_BASE_URL).hostname or ""
    same_site_hosts = {app_base_host}
    if app_base_host.startswith("www."):
        same_site_hosts.add(app_base_host.removeprefix("www."))
    elif app_base_host:
        same_site_hosts.add(f"www.{app_base_host}")

    # Keep the callback on the host the user actually used when it is one of
    # our public domains. This prevents OAuth state from being stored on one
    # host (for example www) and validated on another (for example apex).
    if current_host in same_site_hosts:
        return request_absolute_uri

    return f"{settings.APP_BASE_URL.rstrip('/')}{path}"


def build_authorization_url(request, provider: str, redirect_uri: str, next_url: str | None = None) -> str:
    strategy = load_strategy(request)
    backend_name = get_backend_name(provider)

    try:
        backend = load_backend(strategy, backend_name, redirect_uri)
    except MissingBackend as exc:
        raise SocialAuthServiceError(f"Unsupported provider: {provider}") from exc

    if next_url:
        strategy.session_set("next", next_url)
    return backend.auth_url()


def complete_social_login(request, provider: str, redirect_uri: str) -> SocialLoginResult:
    strategy = load_strategy(request)
    backend_name = get_backend_name(provider)

    try:
        backend = load_backend(strategy, backend_name, redirect_uri)
    except MissingBackend as exc:
        raise SocialAuthServiceError(f"Unsupported provider: {provider}") from exc

    user = backend.complete(user=None)
    if isinstance(user, HttpResponseBase):
        raise SocialAuthServiceError("Social auth returned an unexpected response.")
    if user is None:
        raise SocialAuthServiceError("Social login did not return a user.")

    return SocialLoginResult(
        user=user,
        backend_path=f"{backend.__module__}.{backend.__class__.__name__}",
        provider=get_provider_name(backend.name),
        is_new_user=bool(getattr(user, "is_new", False)),
    )
