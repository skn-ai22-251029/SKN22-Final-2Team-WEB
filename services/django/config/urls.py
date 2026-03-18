from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    # ── Admin ────────────────────────────────────────────────────────────────
    path("admin/", admin.site.urls),

    # ── API — Auth ────────────────────────────────────────────────────────────
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/", include("users.auth_urls")),

    # ── API — Resources ───────────────────────────────────────────────────────
    path("api/users/", include("users.urls")),
    path("api/pets/", include("pets.urls")),
    path("api/orders/", include("orders.urls")),

    # ── Pages (MVT) ───────────────────────────────────────────────────────────
    path("", include("users.page_urls")),
    path("", include("pets.page_urls")),
    path("", include("chat.page_urls")),
    path("", include("orders.page_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
