import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4

import httpx
from django.conf import settings

from ..dto.chat_response import build_stream_error_event


def chat_base_url():
    return settings.FASTAPI_INTERNAL_CHAT_URL.rstrip("/")


def internal_headers(user_id, session_id=None, request_id=None, include_content_type=True):
    headers = {
        "X-User-Id": str(user_id),
        "X-Request-Id": request_id or str(uuid4()),
        "Accept": "text/event-stream",
    }
    if session_id:
        headers["X-Session-Id"] = str(session_id)
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


def _parse_decimal(value):
    if value is None:
        return None

    normalized = str(value).strip().replace(",", "")
    if not normalized or normalized == "-":
        return None

    try:
        return Decimal(normalized)
    except (InvalidOperation, ValueError):
        return None


def _normalize_card_rating(value):
    numeric = _parse_decimal(value)
    if numeric is None:
        return value
    return float(numeric.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def _normalize_card_review_count(value):
    numeric = _parse_decimal(value)
    if numeric is None:
        return value
    return max(int(numeric), 0)


def _normalize_product_card(card):
    if not isinstance(card, dict):
        return card

    normalized = dict(card)
    if "rating" in normalized:
        normalized["rating"] = _normalize_card_rating(normalized.get("rating"))
    if "reviews" in normalized:
        normalized["reviews"] = _normalize_card_review_count(normalized.get("reviews"))
    if "review_count" in normalized:
        normalized["review_count"] = _normalize_card_review_count(normalized.get("review_count"))
    return normalized


def _normalize_sse_payload(payload):
    if not isinstance(payload, dict):
        return payload

    event_type = payload.get("type")
    if event_type not in {"products", "final"}:
        return payload

    cards = payload.get("cards")
    if not isinstance(cards, list):
        return payload

    normalized = dict(payload)
    normalized["cards"] = [_normalize_product_card(card) for card in cards]
    return normalized


def _extract_sse_payload(event_lines):
    payload = None
    for line in event_lines:
        if not line.startswith("data:"):
            continue
        try:
            payload = json.loads(line[5:].strip())
        except json.JSONDecodeError:
            continue
    return payload


def _serialize_sse_event_lines(event_lines, payload):
    serialized_payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    serialized_lines = []
    replaced = False

    for line in event_lines:
        if line.startswith("data:") and not replaced:
            serialized_lines.append(f"data: {serialized_payload}")
            replaced = True
            continue
        if line.startswith("data:"):
            continue
        serialized_lines.append(line)

    if not replaced:
        serialized_lines.append(f"data: {serialized_payload}")

    return "\n".join(serialized_lines) + "\n\n"


def capture_sse_event(event_lines, capture):
    payload = _normalize_sse_payload(_extract_sse_payload(event_lines))
    if not payload:
        return

    event_type = payload.get("type")
    if event_type == "token":
        capture["assistant_text"] += payload.get("content", "")
    elif event_type == "products":
        capture["product_cards"] = payload.get("cards") or []
    elif event_type == "final":
        final_message = (payload.get("message") or "").strip()
        if final_message:
            capture["final_message"] = final_message
            capture["assistant_text"] = final_message
        final_cards = payload.get("cards")
        if final_cards is not None:
            capture["product_cards"] = final_cards or []
        memory_payload = payload.get("memory") or {}
        capture["dialog_state"] = memory_payload.get("dialog_state")
        capture["memory_summary"] = memory_payload.get("memory_summary")
        capture["last_compacted_message_id"] = memory_payload.get("last_compacted_message_id")
        capture["completed"] = True
    elif event_type == "error":
        capture["error_message"] = payload.get("message") or "죄송합니다, 오류가 발생했습니다."
    elif event_type == "done":
        capture["completed"] = True


def stream_fastapi_response(url, payload, user_id, capture=None, request_id=None):
    headers = internal_headers(
        user_id,
        session_id=payload.get("thread_id"),
        request_id=request_id,
    )

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
                                payload = _normalize_sse_payload(_extract_sse_payload(event_lines))
                                if capture is not None:
                                    capture_sse_event(event_lines, capture)
                                if payload:
                                    yield _serialize_sse_event_lines(event_lines, payload)
                                else:
                                    yield "\n".join(event_lines) + "\n\n"
                                event_lines = []
                            continue
                        event_lines.append(line)

                    if event_lines:
                        payload = _normalize_sse_payload(_extract_sse_payload(event_lines))
                        if capture is not None:
                            capture_sse_event(event_lines, capture)
                        if payload:
                            yield _serialize_sse_event_lines(event_lines, payload)
                        else:
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
