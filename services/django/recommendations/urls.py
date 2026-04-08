from django.urls import path

from .api.views import RecommendProxyView

urlpatterns = [
    path("", RecommendProxyView.as_view(), name="recommend-proxy"),
]
