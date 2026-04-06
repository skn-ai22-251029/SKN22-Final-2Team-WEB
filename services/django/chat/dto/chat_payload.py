def build_chat_payload(
    payload,
    user_id,
    thread_id=None,
    target_pet_id=None,
    current_user_message_id=None,
):
    safe_payload = {"user_id": str(user_id)}
    message = (payload.get("message") or "").strip()
    if message and current_user_message_id is None:
        safe_payload["message"] = message

    if thread_id:
        safe_payload["thread_id"] = str(thread_id)
    elif payload.get("thread_id"):
        safe_payload["thread_id"] = payload.get("thread_id")
    else:
        safe_payload["thread_id"] = "default"

    resolved_target_pet_id = target_pet_id or payload.get("target_pet_id")
    if resolved_target_pet_id:
        safe_payload["target_pet_id"] = str(resolved_target_pet_id)

    if current_user_message_id is not None:
        safe_payload["current_user_message_id"] = str(current_user_message_id)

    for key in ("profile_context_type", "pet_profile"):
        value = payload.get(key)
        if value is not None:
            safe_payload[key] = value

    for key in ("health_concerns", "allergies", "food_preferences"):
        values = payload.get(key) or []
        if values:
            safe_payload[key] = values

    return safe_payload
