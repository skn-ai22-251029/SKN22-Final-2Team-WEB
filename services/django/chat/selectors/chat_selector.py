from django.core.exceptions import ValidationError

from ..models import ChatSession


def get_owned_session(user, session_id):
    try:
        return (
            ChatSession.objects.select_related("target_pet")
            .filter(session_id=session_id, user=user)
            .first()
        )
    except (ValidationError, ValueError, TypeError):
        return None
