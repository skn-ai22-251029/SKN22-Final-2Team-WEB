from django.urls import path
from .views import CartView, OrderDetailView, OrderListView, WishlistView

urlpatterns = [
    path("", OrderListView.as_view(), name="order-list"),
    path("<uuid:order_id>/", OrderDetailView.as_view(), name="order-detail"),
    path("cart/", CartView.as_view(), name="order-cart"),
    path("wishlist/", WishlistView.as_view(), name="order-wishlist"),
]
