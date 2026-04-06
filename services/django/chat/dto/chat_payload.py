def build_chat_payload(
    payload,
    user_id,
    thread_id=None,
    target_pet_id=None,
    conversation_history=None,
    memory_summary=None,
    dialog_state=None,
):
    safe_payload = {
        "message": (payload.get("message") or "").strip(),
        "pet_profile": payload.get("pet_profile"),
        "health_concerns": payload.get("health_concerns") or [],
        "allergies": payload.get("allergies") or [],
        "food_preferences": payload.get("food_preferences") or [],
        "user_id": str(user_id),
    }
    if thread_id:
        safe_payload["thread_id"] = str(thread_id)
    elif payload.get("thread_id"):
        safe_payload["thread_id"] = payload.get("thread_id")
    else:
        safe_payload["thread_id"] = "default"

    resolved_target_pet_id = target_pet_id or payload.get("target_pet_id")
    if resolved_target_pet_id:
        safe_payload["target_pet_id"] = str(resolved_target_pet_id)
    if conversation_history is not None:
        safe_payload["conversation_history"] = conversation_history
    if memory_summary is not None:
        safe_payload["memory_summary"] = memory_summary
    if dialog_state is not None:
        safe_payload["dialog_state"] = dialog_state
    return safe_payload
