from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie

from users.onboarding import get_onboarding_redirect_url

from .context_builders import build_chat_page_context


@ensure_csrf_cookie
def chat_view(request):
    onboarding_redirect_url = get_onboarding_redirect_url(request)
    if onboarding_redirect_url:
        return redirect(onboarding_redirect_url)

    return render(
        request,
        "chat/index.html",
        build_chat_page_context(request),
    )
