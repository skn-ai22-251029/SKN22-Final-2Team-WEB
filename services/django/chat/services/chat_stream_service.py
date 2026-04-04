from ..clients.fastapi_chat_client import stream_fastapi_response
from ..models import ChatMessage
from .chat_message_service import persist_recommended_products
from .chat_session_service import touch_session


def persist_streamed_response(session, url, payload, user_id, request_id=None):
    capture = {
        "assistant_text": "",
        "final_message": None,
        "error_message": None,
        "completed": False,
        "product_cards": [],
    }

    try:
        for chunk in stream_fastapi_response(url, payload, user_id, capture=capture, request_id=request_id):
            yield chunk
    finally:
        content = ""
        if capture["error_message"]:
            content = capture["error_message"].strip()
        elif capture["final_message"]:
            content = capture["final_message"].strip()
        elif capture["completed"]:
            content = capture["assistant_text"].strip()

        if content:
            assistant_message = ChatMessage.objects.create(session=session, role="assistant", content=content)
            persist_recommended_products(assistant_message, capture["product_cards"])
            touch_session(session)
