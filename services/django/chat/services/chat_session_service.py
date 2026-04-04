from django.utils import timezone

from ..models import ChatSession


def normalize_profile_context_type(raw_value):
    value = (raw_value or "").strip().lower()
    if value in {
        ChatSession.PROFILE_CONTEXT_PET,
        ChatSession.PROFILE_CONTEXT_FUTURE,
        ChatSession.PROFILE_CONTEXT_NONE,
    }:
        return value
    return ChatSession.PROFILE_CONTEXT_NONE


def touch_session(session):
    session.updated_at = timezone.now()
    session.save(update_fields=["updated_at"])


def update_session_metadata(session, *, title, profile_context_type, target_pet):
    updated_fields = []

    if session.title != title:
        session.title = title
        updated_fields.append("title")

    if session.profile_context_type != profile_context_type:
        session.profile_context_type = profile_context_type
        updated_fields.append("profile_context_type")

    next_target_pet_id = target_pet.pet_id if target_pet else None
    if session.target_pet_id != next_target_pet_id:
        session.target_pet = target_pet
        updated_fields.append("target_pet")

    if updated_fields:
        session.save(update_fields=updated_fields + ["updated_at"])
    else:
        touch_session(session)

    return session
