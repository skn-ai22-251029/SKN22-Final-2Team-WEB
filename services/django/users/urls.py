from django.urls import path

from .views import (
    NicknameAvailabilityView,
    RegisterView,
    UserPhoneVerificationConfirmView,
    UserPhoneVerificationRequestView,
    UserMePreferenceView,
    UserQuickPurchaseDefaultsView,
    UserMeUsedProductView,
    UserMeView,
)

urlpatterns = [
    path("nickname-availability/", NicknameAvailabilityView.as_view(), name="nickname-availability"),
    path("register/", RegisterView.as_view(), name="register"),
    path("me/", UserMeView.as_view(), name="user-me"),
    path("me/quick-purchase/", UserQuickPurchaseDefaultsView.as_view(), name="user-quick-purchase"),
    path("me/phone-verification/request/", UserPhoneVerificationRequestView.as_view(), name="user-phone-verification-request"),
    path("me/phone-verification/confirm/", UserPhoneVerificationConfirmView.as_view(), name="user-phone-verification-confirm"),
    path("me/preferences/", UserMePreferenceView.as_view(), name="user-me-preferences"),
    path("me/used-products/", UserMeUsedProductView.as_view(), name="user-me-used-products"),
]
