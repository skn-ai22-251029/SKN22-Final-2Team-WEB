from django.urls import path

from .views import (
    AuthLoginView,
    AuthLogoutView,
    AuthWithdrawView,
    RegisterView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", AuthLoginView.as_view(), name="auth-login"),
    path("logout/", AuthLogoutView.as_view(), name="auth-logout"),
    path("withdraw/", AuthWithdrawView.as_view(), name="auth-withdraw"),
]
