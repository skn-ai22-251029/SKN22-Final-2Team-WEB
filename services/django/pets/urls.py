from django.urls import path
from .views import PetListView

urlpatterns = [
    path("", PetListView.as_view(), name="pet-list"),
]
