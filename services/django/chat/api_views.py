import httpx
from .api import views as api_view_impl
from .api.serializers import serialize_message as _serialize_message
from .api.serializers import serialize_session as _serialize_session
from .api.serializers import serialize_session_groups as _serialize_session_groups
from .clients.fastapi_chat_client import capture_sse_event as _capture_sse_event
from .clients.fastapi_chat_client import chat_base_url as _chat_base_url
from .clients.fastapi_chat_client import internal_headers as _internal_headers
from .clients.fastapi_chat_client import map_upstream_exception as _map_upstream_exception
from .clients.fastapi_chat_client import stream_fastapi_response as _stream_fastapi_response
from .clients.fastapi_chat_client import stream_timeout as _stream_timeout
from .dto.chat_payload import build_chat_payload as _build_chat_payload
from .dto.chat_response import build_proxy_error_response as _proxy_error_response
from .dto.chat_response import build_stream_error_event as _stream_error_event
from .policies.chat_access_policy import require_authenticated as _require_authenticated
from .selectors.chat_selector import get_owned_session as _get_owned_session
from .selectors.pet_selector import get_owned_target_pet as _get_owned_target_pet
from .services.chat_message_service import persist_recommended_products as _persist_recommended_products
from .services.chat_session_service import normalize_profile_context_type as _normalize_profile_context_type
from .services.chat_session_service import touch_session as _touch_session
from .services.chat_stream_service import persist_streamed_response as _persist_streamed_response

_read_json_body = api_view_impl.read_json_body


def chat_proxy_view(request):
    return api_view_impl.chat_proxy_view(
        request,
        require_authenticated_fn=_require_authenticated,
        read_json_body_fn=_read_json_body,
        build_proxy_error_response_fn=_proxy_error_response,
        build_chat_payload_fn=_build_chat_payload,
        chat_base_url_fn=_chat_base_url,
        stream_fastapi_response_fn=_stream_fastapi_response,
    )


def sessions_proxy_view(request):
    return api_view_impl.sessions_proxy_view(
        request,
        require_authenticated_fn=_require_authenticated,
        read_json_body_fn=_read_json_body,
        build_proxy_error_response_fn=_proxy_error_response,
        serialize_session_fn=_serialize_session,
        serialize_session_groups_fn=_serialize_session_groups,
        normalize_profile_context_type_fn=_normalize_profile_context_type,
        get_owned_target_pet_fn=_get_owned_target_pet,
    )


def session_detail_proxy_view(request, session_id):
    return api_view_impl.session_detail_proxy_view(
        request,
        session_id,
        require_authenticated_fn=_require_authenticated,
        read_json_body_fn=_read_json_body,
        build_proxy_error_response_fn=_proxy_error_response,
        serialize_session_fn=_serialize_session,
        normalize_profile_context_type_fn=_normalize_profile_context_type,
        get_owned_session_fn=_get_owned_session,
        get_owned_target_pet_fn=_get_owned_target_pet,
    )


def session_messages_proxy_view(request, session_id):
    return api_view_impl.session_messages_proxy_view(
        request,
        session_id,
        require_authenticated_fn=_require_authenticated,
        read_json_body_fn=_read_json_body,
        build_proxy_error_response_fn=_proxy_error_response,
        serialize_message_fn=_serialize_message,
        get_owned_session_fn=_get_owned_session,
        build_chat_payload_fn=_build_chat_payload,
        chat_base_url_fn=_chat_base_url,
        persist_streamed_response_fn=_persist_streamed_response,
        touch_session_fn=_touch_session,
    )


__all__ = [
    "chat_proxy_view",
    "session_detail_proxy_view",
    "session_messages_proxy_view",
    "sessions_proxy_view",
    "httpx",
    "_build_chat_payload",
    "_capture_sse_event",
    "_chat_base_url",
    "_get_owned_session",
    "_get_owned_target_pet",
    "_internal_headers",
    "_map_upstream_exception",
    "_normalize_profile_context_type",
    "_persist_recommended_products",
    "_persist_streamed_response",
    "_proxy_error_response",
    "_read_json_body",
    "_require_authenticated",
    "_serialize_message",
    "_serialize_session",
    "_serialize_session_groups",
    "_stream_error_event",
    "_stream_fastapi_response",
    "_stream_timeout",
    "_touch_session",
]
