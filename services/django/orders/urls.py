from django.urls import path

from .api import CartView, OrderDetailView, OrderListView, QuickPurchaseView, WishlistView

urlpatterns = [
    path("", OrderListView.as_view(), name="order-list"),
    path("quick-purchase/", QuickPurchaseView.as_view(), name="order-quick-purchase"),
    path("<uuid:order_id>/", OrderDetailView.as_view(), name="order-detail"),
    path("cart/", CartView.as_view(), name="order-cart"),
    path("wishlist/", WishlistView.as_view(), name="order-wishlist"),
]
