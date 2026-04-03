from django.urls import path

from .pages import catalog, order_complete, order_list, used_products

urlpatterns = [
    path("orders/", order_list, name="order_list"),
    path("orders/complete/<uuid:order_id>/", order_complete, name="order_complete"),
    path("products/", used_products, name="used_products"),
    path("catalog/", catalog, name="catalog"),
]
