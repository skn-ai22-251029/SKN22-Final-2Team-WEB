from dataclasses import dataclass

from django.http import HttpResponseBase
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
