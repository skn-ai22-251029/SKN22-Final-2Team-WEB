from django.urls import path

from .views import SocialLoginView, SocialProviderListView

urlpatterns = [
    path("providers/", SocialProviderListView.as_view(), name="social-provider-list"),
    path("social/<str:provider>/", SocialLoginView.as_view(), name="social-login"),
]
