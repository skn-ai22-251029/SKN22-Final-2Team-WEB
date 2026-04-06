from ..clients.fastapi_chat_client import stream_fastapi_response
from ..models import ChatMessage
from .chat_memory_service import update_session_memory
from .chat_message_service import persist_recommended_products
from .chat_session_service import touch_session


def persist_streamed_response(session, url, payload, user_id, request_id=None):
    capture = {
        "assistant_text": "",
        "final_message": None,
        "error_message": None,
        "completed": False,
        "product_cards": [],
        "dialog_state": None,
        "memory_summary": None,
        "last_compacted_message_id": None,
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
            if not capture["error_message"] and (
                capture["dialog_state"] is not None or capture["memory_summary"] is not None
            ):
                update_session_memory(
                    session,
                    dialog_state=capture["dialog_state"],
                    memory_summary=capture["memory_summary"],
                    last_compacted_message_id=capture["last_compacted_message_id"],
                )
            touch_session(session)
