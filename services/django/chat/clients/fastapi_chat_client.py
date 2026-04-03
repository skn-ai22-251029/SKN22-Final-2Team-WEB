import json

import httpx
from django.conf import settings

from ..dto.chat_response import build_stream_error_event


def chat_base_url():
    return settings.FASTAPI_INTERNAL_CHAT_URL.rstrip("/")


def internal_headers(user_id, include_content_type=True):
    headers = {
        "X-Internal-Service-Token": settings.INTERNAL_SERVICE_TOKEN,
        "X-User-Id": str(user_id),
    }
    if include_content_type:
        headers["Content-Type"] = "application/json"
    return headers


def map_upstream_exception(exc):
    if isinstance(exc, httpx.TimeoutException):
        return "채팅 서버 응답이 지연되고 있습니다. 잠시 후 다시 시도해 주세요.", 504
    return "채팅 서버와 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.", 502


def stream_timeout():
    return httpx.Timeout(
        connect=settings.FASTAPI_STREAM_CONNECT_TIMEOUT,
        read=settings.FASTAPI_STREAM_READ_TIMEOUT,
        write=settings.FASTAPI_STREAM_WRITE_TIMEOUT,
        pool=settings.FASTAPI_STREAM_POOL_TIMEOUT,
    )


def capture_sse_event(event_lines, capture):
    payload = None
    for line in event_lines:
        if not line.startswith("data:"):
            continue
        try:
            payload = json.loads(line[5:].strip())
        except json.JSONDecodeError:
            continue

    if not payload:
        return

    event_type = payload.get("type")
    if event_type == "token":
        capture["assistant_text"] += payload.get("content", "")
    elif event_type == "products":
        capture["product_cards"] = payload.get("cards") or []
    elif event_type == "error":
        capture["error_message"] = payload.get("message") or "죄송합니다, 오류가 발생했습니다."
    elif event_type == "done":
        capture["completed"] = True


def stream_fastapi_response(url, payload, user_id, capture=None):
    headers = internal_headers(user_id)

    try:
        with httpx.Client(timeout=stream_timeout()) as client:
            with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    detail = "채팅 요청 처리에 실패했습니다."
                    try:
                        detail = response.json().get("detail", detail)
                    except Exception:
                        text = response.text.strip()
                        if text:
                            detail = text
                    if capture is not None:
                        capture["error_message"] = detail
                    yield build_stream_error_event(detail)
                    return

                try:
                    event_lines = []
                    for line in response.iter_lines():
                        if line == "":
                            if event_lines:
                                if capture is not None:
                                    capture_sse_event(event_lines, capture)
                                yield "\n".join(event_lines) + "\n\n"
                                event_lines = []
                            continue
                        event_lines.append(line)

                    if event_lines:
                        if capture is not None:
                            capture_sse_event(event_lines, capture)
                        yield "\n".join(event_lines) + "\n\n"
                except httpx.HTTPError as exc:
                    detail, _ = map_upstream_exception(exc)
                    if capture is not None:
                        capture["error_message"] = detail
                    yield build_stream_error_event(detail)
    except httpx.HTTPError as exc:
        detail, _ = map_upstream_exception(exc)
        if capture is not None:
            capture["error_message"] = detail
        yield build_stream_error_event(detail)
