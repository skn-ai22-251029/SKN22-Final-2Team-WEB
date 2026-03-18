from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


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


@login_required
def profile_view(request):
    return render(request, "users/profile.html")
