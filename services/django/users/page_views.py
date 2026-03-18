from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

User = get_user_model()


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
        else:
            user = User.objects.create_user(username=email, email=email, password=password)
            if nickname:
                user.nickname = nickname
                user.save(update_fields=["nickname"])
            login(request, user)
            return redirect("chat")

    return render(request, "users/signup.html", {"error": error})


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def profile_view(request):
    return render(request, "users/profile.html")
