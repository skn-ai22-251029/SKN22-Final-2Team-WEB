from ..models import ChatSessionMemory


def get_or_create_session_memory(session):
    memory, _ = ChatSessionMemory.objects.get_or_create(session=session)
    return memory


def update_session_memory(
    session,
    *,
    dialog_state=None,
    memory_summary=None,
    last_compacted_message_id=None,
):
    memory = get_or_create_session_memory(session)
    updated_fields = []

    if dialog_state is not None and memory.dialog_state != dialog_state:
        memory.dialog_state = dialog_state
        updated_fields.append("dialog_state")
    if memory_summary is not None and memory.summary_text != memory_summary:
        memory.summary_text = memory_summary
        updated_fields.append("summary_text")
    if last_compacted_message_id is not None and memory.last_compacted_message_id != last_compacted_message_id:
        memory.last_compacted_message_id = last_compacted_message_id
        updated_fields.append("last_compacted_message_id")

    if updated_fields:
        memory.save(update_fields=updated_fields + ["updated_at"])

    return memory
