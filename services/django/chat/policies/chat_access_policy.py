from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

_jwt_authentication = JWTAuthentication()


def _authenticate_jwt(request):
    header = _jwt_authentication.get_header(request)
    if header is None:
        return None

    raw_token = _jwt_authentication.get_raw_token(header)
    if raw_token is None:
        raise InvalidToken("유효한 Bearer 토큰이 필요합니다.")

    validated_token = _jwt_authentication.get_validated_token(raw_token)
    user = _jwt_authentication.get_user(validated_token)
    request.user = user
    request.auth = validated_token
    return user


def require_authenticated(request):
    try:
        user = _authenticate_jwt(request)
    except (InvalidToken, TokenError):
        return JsonResponse({"detail": "유효한 인증 토큰이 필요합니다."}, status=401)

    if user is not None:
        return None
    if request.user.is_authenticated:
        return None
    return JsonResponse({"detail": "로그인이 필요합니다."}, status=401)
