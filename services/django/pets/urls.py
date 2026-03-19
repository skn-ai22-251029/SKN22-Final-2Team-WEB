from django.urls import path

from .views import PetDetailView, PetListView

urlpatterns = [
    path("", PetListView.as_view(), name="pet-list"),
    path("<uuid:pet_id>/", PetDetailView.as_view(), name="pet-detail"),
]
