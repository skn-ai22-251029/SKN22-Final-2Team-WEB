from django.http import JsonResponse


def require_authenticated(request):
    if request.user.is_authenticated:
        return None
    return JsonResponse({"detail": "로그인이 필요합니다."}, status=401)
