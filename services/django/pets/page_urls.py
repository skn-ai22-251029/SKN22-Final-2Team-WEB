from django.urls import path

from .pages import (
    pet_add,
    pet_add_details,
    pet_add_future,
    pet_add_health,
    pet_delete_future,
    pet_edit,
    pet_edit_health,
    pet_list,
    preview_pet_edit,
    preview_pet_edit_health,
)

urlpatterns = [
    path("pets/", pet_list, name="pet_list"),
    path("pets/add/", pet_add, name="pet_add"),
    path("pets/add/future/", pet_add_future, name="pet_add_future"),
    path("pets/future/delete/", pet_delete_future, name="pet_delete_future"),
    path("pets/add/details/", pet_add_details, name="pet_add_details"),
    path("pets/add/health/", pet_add_health, name="pet_add_health"),
    path("pets/preview/<str:pet_id>/edit/", preview_pet_edit, name="preview_pet_edit"),
    path("pets/preview/<str:pet_id>/edit/health/", preview_pet_edit_health, name="preview_pet_edit_health"),
    path("pets/<uuid:pet_id>/edit/", pet_edit, name="pet_edit"),
    path("pets/<uuid:pet_id>/edit/health/", pet_edit_health, name="pet_edit_health"),
]
