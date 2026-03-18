from django.urls import path
from . import page_views

urlpatterns = [
    path("pets/", page_views.pet_list, name="pet_list"),
    path("pets/add/", page_views.pet_add, name="pet_add"),
    path("pets/<int:pet_id>/edit/", page_views.pet_edit, name="pet_edit"),
]
