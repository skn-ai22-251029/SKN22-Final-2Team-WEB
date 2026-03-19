from django.urls import path

from .views import (
    RegisterView,
    UserMePreferenceView,
    UserMeUsedProductView,
    UserMeView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("me/", UserMeView.as_view(), name="user-me"),
    path("me/preferences/", UserMePreferenceView.as_view(), name="user-me-preferences"),
    path("me/used-products/", UserMeUsedProductView.as_view(), name="user-me-used-products"),
]
