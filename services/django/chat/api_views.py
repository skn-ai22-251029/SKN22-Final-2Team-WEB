import json

import httpx
from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods


def _chat_base_url():
    return settings.FASTAPI_INTERNAL_CHAT_URL.rstrip("/")


def _internal_headers(user_id, include_content_type=True):
    headers = {
        "X-Internal-Service-Token": settings.INTERNAL_SERVICE_TOKEN,
        "X-User-Id": str(user_id),
    }
    if include_content_type:
        headers["Content-Type"] = "application/json"
    return headers


def _read_json_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("유효한 JSON 요청이 필요합니다.")


def _proxy_json(method, url, user_id, payload=None):
    headers = _internal_headers(user_id, include_content_type=payload is not None)
    with httpx.Client(timeout=30.0) as client:
        response = client.request(method, url, headers=headers, json=payload)

    try:
        data = response.json()
    except ValueError:
        data = {"detail": response.text.strip() or "요청 처리에 실패했습니다."}

    return JsonResponse(data, status=response.status_code, safe=not isinstance(data, list))


def _stream_fastapi_response(url, payload, user_id):
    headers = _internal_headers(user_id)

    with httpx.Client(timeout=None) as client:
        with client.stream("POST", url, headers=headers, json=payload) as response:
            if response.status_code != 200:
                detail = "채팅 요청 처리에 실패했습니다."
                try:
                    detail = response.json().get("detail", detail)
                except Exception:
                    text = response.text.strip()
                    if text:
                        detail = text
                yield f"data: {json.dumps({'type': 'error', 'message': detail}, ensure_ascii=False)}\n\n"
                return

            for chunk in response.iter_bytes():
                if chunk:
                    yield chunk


def _require_authenticated(request):
    if request.user.is_authenticated:
        return None
    return JsonResponse({"detail": "로그인이 필요합니다."}, status=401)


@require_http_methods(["POST"])
def chat_proxy_view(request):
    unauthorized = _require_authenticated(request)
    if unauthorized:
        return unauthorized

    try:
        payload = _read_json_body(request)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)

    message = (payload.get("message") or "").strip()
    if not message:
        return JsonResponse({"detail": "message is required."}, status=400)

    safe_payload = {
        "message": message,
        "thread_id": payload.get("thread_id") or "default",
        "pet_profile": payload.get("pet_profile"),
        "health_concerns": payload.get("health_concerns") or [],
        "allergies": payload.get("allergies") or [],
        "food_preferences": payload.get("food_preferences") or [],
    }

    return StreamingHttpResponse(
        _stream_fastapi_response(_chat_base_url() + "/", safe_payload, request.user.id),
        content_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@require_http_methods(["GET", "POST"])
def sessions_proxy_view(request):
    unauthorized = _require_authenticated(request)
    if unauthorized:
        return unauthorized

    url = _chat_base_url() + "/sessions/"
    if request.method == "GET":
        return _proxy_json("GET", url, request.user.id)

    try:
        payload = _read_json_body(request)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)

    safe_payload = {
        "title": payload.get("title"),
        "target_pet_id": payload.get("target_pet_id"),
    }
    return _proxy_json("POST", url, request.user.id, payload=safe_payload)


@require_http_methods(["PATCH", "DELETE"])
def session_detail_proxy_view(request, session_id):
    unauthorized = _require_authenticated(request)
    if unauthorized:
        return unauthorized

    url = f"{_chat_base_url()}/sessions/{session_id}/"
    if request.method == "DELETE":
        return _proxy_json("DELETE", url, request.user.id)

    try:
        payload = _read_json_body(request)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)

    return _proxy_json("PATCH", url, request.user.id, payload={"title": payload.get("title")})


@require_http_methods(["GET", "POST"])
def session_messages_proxy_view(request, session_id):
    unauthorized = _require_authenticated(request)
    if unauthorized:
        return unauthorized

    url = f"{_chat_base_url()}/sessions/{session_id}/messages/"
    if request.method == "GET":
        return _proxy_json("GET", url, request.user.id)

    try:
        payload = _read_json_body(request)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)

    message = (payload.get("message") or "").strip()
    if not message:
        return JsonResponse({"detail": "message is required."}, status=400)

    safe_payload = {
        "message": message,
        "pet_profile": payload.get("pet_profile"),
        "health_concerns": payload.get("health_concerns") or [],
        "allergies": payload.get("allergies") or [],
        "food_preferences": payload.get("food_preferences") or [],
    }
    return StreamingHttpResponse(
        _stream_fastapi_response(url, safe_payload, request.user.id),
        content_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
