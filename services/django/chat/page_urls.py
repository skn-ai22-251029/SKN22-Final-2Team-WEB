from django.urls import path
from . import page_views

urlpatterns = [
    path("chat/", page_views.chat_view, name="chat"),
]
