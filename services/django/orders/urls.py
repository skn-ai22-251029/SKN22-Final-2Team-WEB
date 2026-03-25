from django.urls import path
from .views import CartView, OrderListView, WishlistView

urlpatterns = [
    path("", OrderListView.as_view(), name="order-list"),
    path("cart/", CartView.as_view(), name="order-cart"),
    path("wishlist/", WishlistView.as_view(), name="order-wishlist"),
]
