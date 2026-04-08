from uuid import uuid4

from pets.models import Pet
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from ..clients import RecommendClientError, request_recommendations


DEFAULT_RECOMMEND_QUERY = "맞춤 상품 추천"
DEFAULT_RECOMMEND_LIMIT = 5
MAX_RECOMMEND_LIMIT = 20


def _request_id(request):
    return request.headers.get("X-Request-Id") or str(uuid4())


def _parse_positive_int(value, *, field_name, default=None, maximum=None):
    if value in (None, ""):
        return default, None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None, Response(
            {"detail": f"{field_name} must be a number.", "code": "invalid_number", "field": field_name},
            status=400,
        )
    if parsed < 0:
        return None, Response(
            {"detail": f"{field_name} must be at least 0.", "code": "invalid_number", "field": field_name},
            status=400,
        )
    if maximum is not None and parsed > maximum:
        return None, Response(
            {
                "detail": f"{field_name} must be at most {maximum}.",
                "code": "invalid_number",
                "field": field_name,
            },
            status=400,
        )
    return parsed, None


def _owned_target_pet_id(user, raw_target_pet_id):
    target_pet_id = (raw_target_pet_id or "").strip()
    if not target_pet_id:
        return None, None

    try:
        exists = Pet.objects.filter(user=user, pet_id=target_pet_id).exists()
    except (TypeError, ValueError):
        return None, Response(
            {"detail": "target_pet_id is invalid.", "code": "invalid_target_pet_id", "field": "target_pet_id"},
            status=400,
        )

    if not exists:
        return None, Response(
            {"detail": "선택한 반려동물을 찾을 수 없습니다.", "code": "target_pet_not_found"},
            status=404,
        )
    return target_pet_id, None


class RecommendProxyView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        request_id = _request_id(request)
        query = (request.query_params.get("query") or DEFAULT_RECOMMEND_QUERY).strip()
        if not query:
            query = DEFAULT_RECOMMEND_QUERY

        limit, error = _parse_positive_int(
            request.query_params.get("limit"),
            field_name="limit",
            default=DEFAULT_RECOMMEND_LIMIT,
            maximum=MAX_RECOMMEND_LIMIT,
        )
        if error is not None:
            error["X-Request-Id"] = request_id
            return error
        if limit < 1:
            response = Response(
                {"detail": "limit must be at least 1.", "code": "invalid_number", "field": "limit"},
                status=400,
            )
            response["X-Request-Id"] = request_id
            return response

        budget, error = _parse_positive_int(
            request.query_params.get("budget"),
            field_name="budget",
        )
        if error is not None:
            error["X-Request-Id"] = request_id
            return error

        target_pet_id, error = _owned_target_pet_id(request.user, request.query_params.get("target_pet_id"))
        if error is not None:
            error["X-Request-Id"] = request_id
            return error

        try:
            payload = request_recommendations(
                user_id=request.user.id,
                query=query,
                target_pet_id=target_pet_id,
                pet_type=(request.query_params.get("pet_type") or "").strip() or None,
                category=(request.query_params.get("category") or "").strip() or None,
                subcategory=(request.query_params.get("subcategory") or "").strip() or None,
                budget=budget,
                limit=limit,
                request_id=request_id,
            )
        except RecommendClientError as exc:
            response = Response({"detail": exc.detail, "code": exc.code}, status=exc.status_code)
            response["X-Request-Id"] = request_id
            return response

        response = Response(payload)
        response["X-Request-Id"] = request_id
        return response
