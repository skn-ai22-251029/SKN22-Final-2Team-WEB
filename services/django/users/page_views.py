from types import SimpleNamespace

from django.contrib.auth import get_user_model, logout
from django.shortcuts import redirect, render

User = get_user_model()


def home(request):
    if request.user.is_authenticated:
        return redirect("chat")
    return render(request, "chat/index.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("chat")
    return render(request, "users/login.html")


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("chat")
    return render(request, "users/signup.html")


def logout_view(request):
    logout(request)
    return redirect("login")


def profile_view(request):
    preview_mode = request.GET.get("preview") == "1" or not request.user.is_authenticated

    if request.method == "POST":
        if preview_mode:
            return redirect("/pets/add/?preview=1")
        return redirect("pet_add")

    profile = getattr(request.user, "profile", None) if request.user.is_authenticated else None
    profile_data = SimpleNamespace(
        nickname=getattr(profile, "nickname", ""),
        phone=getattr(profile, "phone", ""),
    )
    return render(
        request,
        "users/profile.html",
        {
            "profile": profile_data,
            "profile_preview": preview_mode,
        },
    )
