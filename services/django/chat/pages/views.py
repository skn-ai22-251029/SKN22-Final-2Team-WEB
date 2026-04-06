from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie

from users.onboarding import get_onboarding_redirect_url
from users.services.auth_service import issue_user_tokens
from users.social_auth import SOCIAL_AUTH_ACCESS_SESSION_KEY, SOCIAL_AUTH_REFRESH_SESSION_KEY

from .context_builders import build_chat_page_context


def ensure_chat_api_tokens(
    request,
    *,
    issue_user_tokens_fn=issue_user_tokens,
    access_session_key=SOCIAL_AUTH_ACCESS_SESSION_KEY,
    refresh_session_key=SOCIAL_AUTH_REFRESH_SESSION_KEY,
):
    if not request.user.is_authenticated:
        return

    tokens = issue_user_tokens_fn(request.user)
    request.session[access_session_key] = tokens["access"]
    request.session[refresh_session_key] = tokens["refresh"]


@ensure_csrf_cookie
def chat_view(request):
    onboarding_redirect_url = get_onboarding_redirect_url(request)
    if onboarding_redirect_url:
        return redirect(onboarding_redirect_url)

    ensure_chat_api_tokens(request)

    return render(
        request,
        "chat/index.html",
        build_chat_page_context(request),
    )
