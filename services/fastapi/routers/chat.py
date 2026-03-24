import asyncio
import hmac
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from core.db import SessionLocal
from core.models import ChatMessageModel, ChatSessionModel, PetModel
from pipeline.chatbot_graph import build_graph

router = APIRouter()

SEOUL_TZ = ZoneInfo("Asia/Seoul")
MAX_HISTORY_CHARS = int(os.getenv("CHAT_HISTORY_MAX_CHARS", "4000"))
RECENT_HISTORY_CHARS = int(os.getenv("CHAT_HISTORY_RECENT_CHARS", "1800"))
SUMMARY_PREVIEW_CHARS = int(os.getenv("CHAT_HISTORY_SUMMARY_CHARS", "700"))
DEFAULT_SESSION_TITLE = "새 대화"

# 앱 기동 시 한 번만 빌드 (MemorySaver 포함)
_graph = None
_internal_service_token = os.getenv("INTERNAL_SERVICE_TOKEN", "dev-internal-token")


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"
    pet_profile: Optional[dict] = None
    health_concerns: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    food_preferences: list[str] = Field(default_factory=list)


class SessionCreateRequest(BaseModel):
    title: str | None = None
    target_pet_id: str | None = None


class SessionUpdateRequest(BaseModel):
    title: str


class SessionMessageRequest(BaseModel):
    message: str
    pet_profile: Optional[dict] = None
    health_concerns: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    food_preferences: list[str] = Field(default_factory=list)


def _sse(event_type: str, data: dict) -> str:
    return f"data: {json.dumps({'type': event_type, **data}, ensure_ascii=False)}\n\n"


def _verify_internal_request(service_token: str | None, user_id: str | None) -> int:
    if not service_token or not hmac.compare_digest(service_token, _internal_service_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-User-Id header is required.")
    try:
        return int(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-User-Id must be an integer.") from exc


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_seoul(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(SEOUL_TZ)


def _session_title_from_message(message: str) -> str:
    compact = " ".join((message or "").split()).strip()
    if not compact:
        return DEFAULT_SESSION_TITLE
    return compact if len(compact) <= 24 else compact[:23].rstrip() + "…"


def _trim_text(text: str, limit: int) -> str:
    compact = " ".join((text or "").split()).strip()
    if len(compact) <= limit:
        return compact
    return compact[: max(0, limit - 1)].rstrip() + "…"


def _serialize_session(session: ChatSessionModel) -> dict:
    created_at = _as_seoul(session.created_at)
    updated_at = _as_seoul(session.updated_at)
    return {
        "session_id": str(session.session_id),
        "title": session.title,
        "target_pet_id": str(session.target_pet_id) if session.target_pet_id else None,
        "created_at": created_at.isoformat(),
        "updated_at": updated_at.isoformat(),
        "display_date": created_at.strftime("%y/%m/%d"),
    }


def _serialize_message(message: ChatMessageModel) -> dict:
    created_at = _as_seoul(message.created_at)
    return {
        "message_id": str(message.message_id),
        "role": message.role,
        "content": message.content,
        "created_at": created_at.isoformat(),
    }


def _group_key(reference: datetime, compared: datetime) -> str:
    ref_date = _as_seoul(reference).date()
    compared_date = _as_seoul(compared).date()
    if compared_date == ref_date:
        return "today"
    if compared_date == ref_date - timedelta(days=1):
        return "yesterday"
    if compared_date >= ref_date - timedelta(days=7):
        return "last_7_days"
    return "older"


def _build_grouped_sessions(sessions: list[ChatSessionModel]) -> dict:
    now = _now()
    grouped = {
        "today": {"key": "today", "label": "오늘", "sessions": []},
        "yesterday": {"key": "yesterday", "label": "어제", "sessions": []},
        "last_7_days": {"key": "last_7_days", "label": "7일 이내", "sessions": []},
        "older": {"key": "older", "label": "이전", "sessions": []},
    }
    serialized = []

    for session in sessions:
        payload = _serialize_session(session)
        serialized.append(payload)
        grouped[_group_key(now, session.updated_at)]["sessions"].append(payload)

    return {
        "sessions": serialized,
        "groups": [group for group in grouped.values() if group["sessions"]],
    }


def _build_history_context(messages: list[ChatMessageModel]) -> tuple[str, bool]:
    if not messages:
        return "", False

    rendered = [
        f"{'사용자' if message.role == 'user' else 'AI'}: {_trim_text(message.content, 280)}"
        for message in messages
        if (message.content or "").strip()
    ]
    if not rendered:
        return "", False

    full_text = "\n".join(rendered)
    if len(full_text) <= MAX_HISTORY_CHARS:
        return full_text, False

    recent_lines = []
    recent_chars = 0
    for line in reversed(rendered):
        extra = len(line) + 1
        if recent_lines and recent_chars + extra > RECENT_HISTORY_CHARS:
            break
        recent_lines.append(line)
        recent_chars += extra
    recent_lines.reverse()

    older_lines = rendered[: len(rendered) - len(recent_lines)]
    summary = " / ".join(_trim_text(line, 100) for line in older_lines[-6:])
    summary = _trim_text(summary, SUMMARY_PREVIEW_CHARS)

    parts = []
    if summary:
        parts.append("[이전 대화 요약]")
        parts.append(summary)
    if recent_lines:
        parts.append("[최근 대화]")
        parts.extend(recent_lines)
    return "\n".join(parts), True


def _get_session_or_404(db, user_id: int, session_id: uuid.UUID) -> ChatSessionModel:
    session = db.execute(
        select(ChatSessionModel).where(
            ChatSessionModel.session_id == session_id,
            ChatSessionModel.user_id == user_id,
        )
    ).scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다.")
    return session


def _validate_target_pet(db, user_id: int, target_pet_id: str | None) -> uuid.UUID | None:
    if not target_pet_id:
        return None
    try:
        pet_uuid = uuid.UUID(target_pet_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="target_pet_id 형식이 올바르지 않습니다.") from exc

    pet = db.execute(
        select(PetModel).where(
            PetModel.pet_id == pet_uuid,
            PetModel.user_id == user_id,
        )
    ).scalar_one_or_none()
    if not pet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="반려동물을 찾을 수 없습니다.")
    return pet_uuid


def _build_initial_state(req: ChatRequest | SessionMessageRequest, user_id: int, history_context: str = "") -> dict:
    return {
        "messages": [],
        "user_input": req.message,
        "user_id": str(user_id),
        "pet_profile": req.pet_profile,
        "health_concerns": req.health_concerns,
        "allergies": req.allergies,
        "food_preferences": req.food_preferences,
        "conversation_history": history_context,
        "intents": [],
        "domain_intent": None,
        "clarification_count": 0,
        "detected_aspect": None,
        "budget": None,
        "search_query": None,
        "filters": None,
        "search_results": [],
        "reranked_results": [],
        "filter_relaxation_count": 0,
        "domain_contexts": [],
        "response": "",
        "product_cards": [],
    }


async def _run_graph(req: ChatRequest | SessionMessageRequest, thread_id: str, user_id: int, history_context: str = ""):
    graph = get_graph()
    initial_state = _build_initial_state(req, user_id=user_id, history_context=history_context)
    config = {"configurable": {"thread_id": thread_id}}

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: graph.invoke(initial_state, config=config),
    )


async def _legacy_stream(req: ChatRequest, user_id: int):
    try:
        final_state = await _run_graph(req, thread_id=req.thread_id, user_id=user_id)
    except Exception as exc:
        yield _sse("error", {"message": str(exc)})
        return

    response_text = final_state.get("response", "")
    product_cards = final_state.get("product_cards", [])

    words = response_text.split(" ")
    for index, word in enumerate(words):
        chunk = word if index == 0 else " " + word
        yield _sse("token", {"content": chunk})
        await asyncio.sleep(0.03)

    if product_cards:
        yield _sse("products", {"cards": product_cards})

    yield _sse("done", {})


async def _session_message_stream(
    session_id: uuid.UUID,
    req: SessionMessageRequest,
    user_id: int,
    history_context: str,
):
    try:
        final_state = await _run_graph(req, thread_id=str(session_id), user_id=user_id, history_context=history_context)
    except Exception as exc:
        yield _sse("error", {"message": str(exc)})
        return

    response_text = final_state.get("response", "")
    product_cards = final_state.get("product_cards", [])

    with SessionLocal() as db:
        session = _get_session_or_404(db, user_id, session_id)
        session.updated_at = _now()
        db.add(
            ChatMessageModel(
                message_id=uuid.uuid4(),
                session_id=session_id,
                role="assistant",
                content=response_text,
                created_at=_now(),
            )
        )
        db.add(session)
        db.commit()

    words = response_text.split(" ")
    for index, word in enumerate(words):
        chunk = word if index == 0 else " " + word
        yield _sse("token", {"content": chunk})
        await asyncio.sleep(0.03)

    if product_cards:
        yield _sse("products", {"cards": product_cards})

    yield _sse("done", {})


@router.get("/sessions/")
def list_sessions(
    x_internal_service_token: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
):
    user_id = _verify_internal_request(x_internal_service_token, x_user_id)
    with SessionLocal() as db:
        sessions = db.execute(
            select(ChatSessionModel)
            .where(ChatSessionModel.user_id == user_id)
            .order_by(ChatSessionModel.updated_at.desc(), ChatSessionModel.created_at.desc())
            .limit(50)
        ).scalars().all()
    return _build_grouped_sessions(sessions)


@router.post("/sessions/", status_code=status.HTTP_201_CREATED)
def create_session(
    req: SessionCreateRequest,
    x_internal_service_token: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
):
    user_id = _verify_internal_request(x_internal_service_token, x_user_id)
    with SessionLocal() as db:
        pet_id = _validate_target_pet(db, user_id, req.target_pet_id)
        now = _now()
        session = ChatSessionModel(
            session_id=uuid.uuid4(),
            user_id=user_id,
            target_pet_id=pet_id,
            title=(req.title or "").strip() or DEFAULT_SESSION_TITLE,
            created_at=now,
            updated_at=now,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return _serialize_session(session)


@router.patch("/sessions/{session_id}/")
def update_session(
    session_id: uuid.UUID,
    req: SessionUpdateRequest,
    x_internal_service_token: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
):
    user_id = _verify_internal_request(x_internal_service_token, x_user_id)
    title = (req.title or "").strip()
    if not title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="title is required.")

    with SessionLocal() as db:
        session = _get_session_or_404(db, user_id, session_id)
        session.title = title
        session.updated_at = _now()
        db.add(session)
        db.commit()
        db.refresh(session)
        return _serialize_session(session)


@router.delete("/sessions/{session_id}/")
def delete_session(
    session_id: uuid.UUID,
    x_internal_service_token: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
):
    user_id = _verify_internal_request(x_internal_service_token, x_user_id)
    with SessionLocal() as db:
        session = _get_session_or_404(db, user_id, session_id)
        db.delete(session)
        db.commit()
    return {"deleted": True, "session_id": str(session_id)}


@router.get("/sessions/{session_id}/messages/")
def list_messages(
    session_id: uuid.UUID,
    x_internal_service_token: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
):
    user_id = _verify_internal_request(x_internal_service_token, x_user_id)
    with SessionLocal() as db:
        _get_session_or_404(db, user_id, session_id)
        messages = db.execute(
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == session_id)
            .order_by(ChatMessageModel.created_at.asc())
        ).scalars().all()
        _, trimmed = _build_history_context(messages)
    return {
        "session_id": str(session_id),
        "messages": [_serialize_message(message) for message in messages],
        "history_trimmed": trimmed,
    }


@router.post("/sessions/{session_id}/messages/")
async def post_message(
    session_id: uuid.UUID,
    req: SessionMessageRequest,
    x_internal_service_token: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
):
    user_id = _verify_internal_request(x_internal_service_token, x_user_id)
    message = (req.message or "").strip()
    if not message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="message is required.")

    with SessionLocal() as db:
        session = _get_session_or_404(db, user_id, session_id)
        existing_messages = db.execute(
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == session_id)
            .order_by(ChatMessageModel.created_at.asc())
        ).scalars().all()
        history_context, _ = _build_history_context(existing_messages)

        if not session.title or session.title == DEFAULT_SESSION_TITLE:
            session.title = _session_title_from_message(message)
        session.updated_at = _now()

        db.add(
            ChatMessageModel(
                message_id=uuid.uuid4(),
                session_id=session_id,
                role="user",
                content=message,
                created_at=_now(),
            )
        )
        db.add(session)
        db.commit()

    return StreamingResponse(
        _session_message_stream(session_id=session_id, req=req, user_id=user_id, history_context=history_context),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/")
async def chat(
    req: ChatRequest,
    x_internal_service_token: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
):
    user_id = _verify_internal_request(x_internal_service_token, x_user_id)
    return StreamingResponse(
        _legacy_stream(req, user_id=user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
