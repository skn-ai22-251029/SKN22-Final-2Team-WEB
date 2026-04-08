from django.urls import path
from . import page_views

urlpatterns = [
    path("", page_views.home, name="home"),
    path("login/", page_views.login_view, name="login"),
    path("vendor/login/", page_views.vendor_login_view, name="vendor-login"),
    path("vendor/logout/", page_views.vendor_logout_view, name="vendor-logout"),
    path("vendor/dashboard/", page_views.vendor_dashboard_view, name="vendor-dashboard"),
    path("vendor/analytics/", page_views.vendor_analytics_view, name="vendor-analytics"),
    path("vendor/products/", page_views.vendor_products_view, name="vendor-products"),
    path("vendor/products/new/", page_views.vendor_product_create_view, name="vendor-product-create"),
    path("vendor/products/<str:goods_id>/edit/", page_views.vendor_product_edit_view, name="vendor-product-edit"),
    path("vendor/products/<str:goods_id>/", page_views.vendor_product_detail_view, name="vendor-product-detail"),
    path("vendor/orders/", page_views.vendor_orders_view, name="vendor-orders"),
    path("vendor/reviews/", page_views.vendor_reviews_view, name="vendor-reviews"),
    path("signup/", page_views.signup_view, name="signup"),
    path("logout/", page_views.logout_view, name="logout"),
    path("profile/", page_views.profile_view, name="profile"),
    path("profile/withdraw/", page_views.profile_withdraw_view, name="profile-withdraw"),
    path("auth/<str:provider>/start/", page_views.social_login_start_view, name="social-login-start"),
    path("auth/<str:provider>/callback/", page_views.social_login_callback_view, name="social-login-callback"),
]
