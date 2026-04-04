import json

from django.http import JsonResponse


def build_proxy_error_response(detail, status):
    return JsonResponse({"detail": detail}, status=status)


def build_stream_error_event(message):
    payload = {"type": "error", "message": message}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
