import json
from uuid import uuid4

from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods

from ..api.serializers import serialize_message, serialize_session, serialize_session_groups
from ..clients.fastapi_chat_client import chat_base_url, stream_fastapi_response
from ..dto.chat_payload import build_chat_payload
from ..dto.chat_response import build_proxy_error_response
from ..models import ChatMessage, ChatSession
from ..policies.chat_access_policy import require_authenticated
from ..selectors.chat_selector import get_owned_session
from ..selectors.pet_selector import get_owned_target_pet
from ..services.chat_memory_service import build_memory_payload, get_or_create_session_memory
from ..services.chat_session_service import (
    normalize_profile_context_type,
    touch_session,
    update_session_metadata,
)
from ..services.chat_stream_service import persist_streamed_response


def read_json_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("유효한 JSON 요청이 필요합니다.")


def build_request_id(request):
    return request.headers.get("X-Request-Id") or str(uuid4())


@require_http_methods(["POST"])
def chat_proxy_view(
    request,
    *,
    require_authenticated_fn=require_authenticated,
    read_json_body_fn=read_json_body,
    build_proxy_error_response_fn=build_proxy_error_response,
    build_chat_payload_fn=build_chat_payload,
    chat_base_url_fn=chat_base_url,
    stream_fastapi_response_fn=stream_fastapi_response,
):
    unauthorized = require_authenticated_fn(request)
    if unauthorized:
        return unauthorized

    try:
        payload = read_json_body_fn(request)
    except ValueError as exc:
        return build_proxy_error_response_fn(str(exc), status=400)

    message = (payload.get("message") or "").strip()
    if not message:
        return build_proxy_error_response_fn("message is required.", status=400)

    request_id = build_request_id(request)
    safe_payload = build_chat_payload_fn(payload, request.user.id, target_pet_id=payload.get("target_pet_id"))

    return StreamingHttpResponse(
        stream_fastapi_response_fn(chat_base_url_fn() + "/", safe_payload, request.user.id, request_id=request_id),
        content_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Request-Id": request_id,
            "X-Accel-Buffering": "no",
        },
    )


@require_http_methods(["GET", "POST"])
def sessions_proxy_view(
    request,
    *,
    require_authenticated_fn=require_authenticated,
    read_json_body_fn=read_json_body,
    build_proxy_error_response_fn=build_proxy_error_response,
    serialize_session_fn=serialize_session,
    serialize_session_groups_fn=serialize_session_groups,
    normalize_profile_context_type_fn=normalize_profile_context_type,
    get_owned_target_pet_fn=get_owned_target_pet,
    get_or_create_session_memory_fn=get_or_create_session_memory,
):
    unauthorized = require_authenticated_fn(request)
    if unauthorized:
        return unauthorized

    if request.method == "GET":
        sessions = list(
            request.user.chat_sessions.select_related("target_pet").order_by("-updated_at", "-created_at")
        )
        return JsonResponse(
            {
                "sessions": [serialize_session_fn(session) for session in sessions],
                "groups": serialize_session_groups_fn(sessions),
            }
        )

    try:
        payload = read_json_body_fn(request)
    except ValueError as exc:
        return build_proxy_error_response_fn(str(exc), status=400)

    title = (payload.get("title") or "").strip() or "새 대화"
    target_pet_id = payload.get("target_pet_id")
    profile_context_type = normalize_profile_context_type_fn(payload.get("profile_context_type"))
    target_pet = None
    if profile_context_type == ChatSession.PROFILE_CONTEXT_PET and target_pet_id:
        target_pet = get_owned_target_pet_fn(request.user, target_pet_id)
        if target_pet is None:
            return build_proxy_error_response_fn("선택한 반려동물을 찾을 수 없습니다.", status=404)

    session = ChatSession.objects.create(
        user=request.user,
        target_pet=target_pet,
        profile_context_type=profile_context_type,
        title=title,
    )
    get_or_create_session_memory_fn(session)
    return JsonResponse(serialize_session_fn(session), status=201)


@require_http_methods(["PATCH", "DELETE"])
def session_detail_proxy_view(
    request,
    session_id,
    *,
    require_authenticated_fn=require_authenticated,
    read_json_body_fn=read_json_body,
    build_proxy_error_response_fn=build_proxy_error_response,
    serialize_session_fn=serialize_session,
    normalize_profile_context_type_fn=normalize_profile_context_type,
    get_owned_session_fn=get_owned_session,
    get_owned_target_pet_fn=get_owned_target_pet,
):
    unauthorized = require_authenticated_fn(request)
    if unauthorized:
        return unauthorized

    session = get_owned_session_fn(request.user, session_id)
    if session is None:
        return build_proxy_error_response_fn("대화를 찾을 수 없습니다.", status=404)

    if request.method == "DELETE":
        session.delete()
        return JsonResponse({"deleted": True})

    try:
        payload = read_json_body_fn(request)
    except ValueError as exc:
        return build_proxy_error_response_fn(str(exc), status=400)

    next_title = (payload.get("title") or "").strip() or session.title or "새 대화"
    next_profile_context_type = normalize_profile_context_type_fn(
        payload.get("profile_context_type") or session.profile_context_type
    )
    next_target_pet = session.target_pet

    if next_profile_context_type == ChatSession.PROFILE_CONTEXT_PET:
        requested_target_pet_id = payload.get("target_pet_id") or session.target_pet_id
        if requested_target_pet_id:
            next_target_pet = get_owned_target_pet_fn(request.user, requested_target_pet_id)
            if next_target_pet is None:
                return build_proxy_error_response_fn("선택한 반려동물을 찾을 수 없습니다.", status=404)
        else:
            next_target_pet = None
    else:
        next_target_pet = None

    update_session_metadata(
        session,
        title=next_title,
        profile_context_type=next_profile_context_type,
        target_pet=next_target_pet,
    )
    return JsonResponse(serialize_session_fn(session))


@require_http_methods(["GET", "POST"])
def session_messages_proxy_view(
    request,
    session_id,
    *,
    require_authenticated_fn=require_authenticated,
    read_json_body_fn=read_json_body,
    build_proxy_error_response_fn=build_proxy_error_response,
    serialize_message_fn=serialize_message,
    get_owned_session_fn=get_owned_session,
    build_chat_payload_fn=build_chat_payload,
    chat_base_url_fn=chat_base_url,
    persist_streamed_response_fn=persist_streamed_response,
    touch_session_fn=touch_session,
    build_memory_payload_fn=build_memory_payload,
):
    unauthorized = require_authenticated_fn(request)
    if unauthorized:
        return unauthorized

    session = get_owned_session_fn(request.user, session_id)
    if session is None:
        return build_proxy_error_response_fn("대화를 찾을 수 없습니다.", status=404)

    if request.method == "GET":
        messages = [
            serialize_message_fn(message)
            for message in session.messages.prefetch_related("recommended_products__product").order_by("created_at")
        ]
        return JsonResponse(
            {
                "session_id": str(session.session_id),
                "messages": messages,
                "history_trimmed": False,
            }
        )

    try:
        payload = read_json_body_fn(request)
    except ValueError as exc:
        return build_proxy_error_response_fn(str(exc), status=400)

    message = (payload.get("message") or "").strip()
    if not message:
        return build_proxy_error_response_fn("message is required.", status=400)

    user_message = ChatMessage.objects.create(session=session, role="user", content=message)
    touch_session_fn(session)
    memory_payload = build_memory_payload_fn(session, exclude_message_id=user_message.message_id)

    request_id = build_request_id(request)
    safe_payload = build_chat_payload_fn(
        payload,
        request.user.id,
        thread_id=session.session_id,
        target_pet_id=session.target_pet_id,
        conversation_history=memory_payload["conversation_history"],
        memory_summary=memory_payload["memory_summary"],
        dialog_state=memory_payload["dialog_state"],
    )
    return StreamingHttpResponse(
        persist_streamed_response_fn(
            session,
            chat_base_url_fn() + "/",
            safe_payload,
            request.user.id,
            request_id=request_id,
        ),
        content_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Request-Id": request_id,
            "X-Accel-Buffering": "no",
        },
    )
