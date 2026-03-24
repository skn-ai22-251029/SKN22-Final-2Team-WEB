from django.urls import path
from . import page_views

urlpatterns = [
    path("pets/", page_views.pet_list, name="pet_list"),
    path("pets/add/", page_views.pet_add, name="pet_add"),
    path("pets/add/future/", page_views.pet_add_future, name="pet_add_future"),
    path("pets/future/delete/", page_views.pet_delete_future, name="pet_delete_future"),
    path("pets/add/details/", page_views.pet_add_details, name="pet_add_details"),
    path("pets/add/health/", page_views.pet_add_health, name="pet_add_health"),
    path("pets/preview/<str:pet_id>/edit/", page_views.preview_pet_edit, name="preview_pet_edit"),
    path("pets/preview/<str:pet_id>/edit/health/", page_views.preview_pet_edit_health, name="preview_pet_edit_health"),
    path("pets/<uuid:pet_id>/edit/", page_views.pet_edit, name="pet_edit"),
    path("pets/<uuid:pet_id>/edit/health/", page_views.pet_edit_health, name="pet_edit_health"),
]
