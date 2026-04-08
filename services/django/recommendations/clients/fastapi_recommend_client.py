from uuid import uuid4

import httpx
from django.conf import settings


class RecommendClientError(RuntimeError):
    def __init__(self, detail, *, status_code=502, code="recommendation_upstream_failed"):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.code = code


def recommend_base_url():
    return settings.FASTAPI_INTERNAL_RECOMMEND_URL.rstrip("/")


def recommend_timeout():
    return httpx.Timeout(
        connect=settings.FASTAPI_STREAM_CONNECT_TIMEOUT,
        read=settings.FASTAPI_STREAM_READ_TIMEOUT,
        write=settings.FASTAPI_STREAM_WRITE_TIMEOUT,
        pool=settings.FASTAPI_STREAM_POOL_TIMEOUT,
    )


def build_internal_headers(user_id, request_id=None):
    return {
        "X-User-Id": str(user_id),
        "X-Request-Id": request_id or str(uuid4()),
        "Accept": "application/json",
    }


def _extract_error_detail(response):
    try:
        payload = response.json()
    except Exception:
        payload = None

    if isinstance(payload, dict):
        return payload.get("detail") or payload.get("message") or "추천 상품을 조회하지 못했습니다."

    text = response.text.strip()
    return text or "추천 상품을 조회하지 못했습니다."


def _raise_for_upstream_status(response):
    if response.status_code < 400:
        return

    status_code = response.status_code if response.status_code < 500 else 502
    code = "recommendation_upstream_rejected" if status_code < 500 else "recommendation_upstream_failed"
    raise RecommendClientError(
        _extract_error_detail(response),
        status_code=status_code,
        code=code,
    )


def request_recommendations(
    *,
    user_id,
    query,
    target_pet_id=None,
    pet_type=None,
    category=None,
    subcategory=None,
    budget=None,
    limit=5,
    request_id=None,
):
    params = {
        "query": query,
        "limit": limit,
    }
    optional_params = {
        "target_pet_id": target_pet_id,
        "pet_type": pet_type,
        "category": category,
        "subcategory": subcategory,
        "budget": budget,
    }
    for key, value in optional_params.items():
        if value not in (None, ""):
            params[key] = value

    try:
        with httpx.Client(timeout=recommend_timeout()) as client:
            response = client.get(
                recommend_base_url() + "/",
                headers=build_internal_headers(user_id, request_id=request_id),
                params=params,
            )
    except httpx.TimeoutException as exc:
        raise RecommendClientError(
            "추천 서버 응답이 지연되고 있습니다. 잠시 후 다시 시도해 주세요.",
            status_code=504,
            code="recommendation_timeout",
        ) from exc
    except httpx.HTTPError as exc:
        raise RecommendClientError(
            "추천 서버와 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.",
            status_code=502,
            code="recommendation_connection_failed",
        ) from exc

    _raise_for_upstream_status(response)
    try:
        return response.json()
    except ValueError as exc:
        raise RecommendClientError(
            "추천 서버 응답 형식이 올바르지 않습니다.",
            status_code=502,
            code="recommendation_invalid_response",
        ) from exc
