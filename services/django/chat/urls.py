from django.urls import path

from . import api_views

urlpatterns = [
    path("", api_views.chat_proxy_view, name="chat-proxy"),
    path("sessions/", api_views.sessions_proxy_view, name="chat-sessions-proxy"),
    path("sessions/<uuid:session_id>/", api_views.session_detail_proxy_view, name="chat-session-detail-proxy"),
    path("sessions/<uuid:session_id>/messages/", api_views.session_messages_proxy_view, name="chat-session-messages-proxy"),
]
