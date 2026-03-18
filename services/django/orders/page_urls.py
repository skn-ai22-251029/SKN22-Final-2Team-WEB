from django.urls import path
from . import page_views

urlpatterns = [
    path("orders/", page_views.order_list, name="order_list"),
    path("products/", page_views.used_products, name="used_products"),
]
