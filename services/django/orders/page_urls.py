from django.urls import path
from . import page_views

urlpatterns = [
    path("orders/", page_views.order_list, name="order_list"),
    path("orders/complete/<uuid:order_id>/", page_views.order_complete, name="order_complete"),
    path("products/", page_views.used_products, name="used_products"),
]
