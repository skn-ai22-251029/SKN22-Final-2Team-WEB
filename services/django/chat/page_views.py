from django.shortcuts import render


def chat_view(request):
    sessions = []
    if request.user.is_authenticated:
        sessions = list(
            request.user.chat_sessions.order_by("-created_at").values("session_id", "title", "created_at")[:50]
        )
    return render(request, "chat/index.html", {"sessions": sessions})
