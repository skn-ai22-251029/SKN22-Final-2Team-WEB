from django.urls import path

from .views import AuthLoginView, AuthLogoutView, AuthWithdrawView, SocialLoginView, SocialProviderListView

urlpatterns = [
    path("login/", AuthLoginView.as_view(), name="auth-login"),
    path("logout/", AuthLogoutView.as_view(), name="auth-logout"),
    path("withdraw/", AuthWithdrawView.as_view(), name="auth-withdraw"),
    path("providers/", SocialProviderListView.as_view(), name="social-provider-list"),
    path("social/<str:provider>/", SocialLoginView.as_view(), name="social-login"),
]
