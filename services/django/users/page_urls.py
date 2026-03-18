from django.urls import path
from . import page_views

urlpatterns = [
    path("", page_views.home, name="home"),
    path("login/", page_views.login_view, name="login"),
    path("signup/", page_views.signup_view, name="signup"),
    path("logout/", page_views.logout_view, name="logout"),
    path("profile/", page_views.profile_view, name="profile"),
    path("auth/<str:provider>/start/", page_views.social_login_start_view, name="social-login-start"),
    path("auth/<str:provider>/callback/", page_views.social_login_callback_view, name="social-login-callback"),
]
