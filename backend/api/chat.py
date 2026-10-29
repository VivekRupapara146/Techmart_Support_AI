"""
Legacy chat endpoint (unprefixed). Kept byte-for-byte compatible with the
original Milestone response shape (APIResponse envelope) so the existing
test suite keeps passing unchanged. The real pipeline logic now lives in
core/chat_pipeline.py, shared with the versioned /v1/chat endpoint in
api/v1_chat.py — see that module for the richer contract (telemetry,
evidence, router override) the React frontend actually speaks.
"""
import uuid

from fastapi import APIRouter, Depends, Request, HTTPException, status, Path
from pydantic import BaseModel, Field

from auth.jwt_handler import get_current_subject
from core.rate_limit import limiter
from core.config import settings
from core.chat_pipeline import run_chat_pipeline
from database.mongo import get_db
from database.conversations import append_message, get_history, list_sessions
from models.response import APIResponse
from models.conversation import Message, ConversationHistoryData, SessionListData

router_ = APIRouter(prefix="/chat", tags=["chat (legacy, unprefixed)"])

SESSION_ID_PATTERN = r"^[a-zA-Z0-9\-]{1,64}$"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, pattern=SESSION_ID_PATTERN)


class ChatResponseData(BaseModel):
    reply: str
    routed_agents: list[str]
    session_id: str


@router_.post("", response_model=APIResponse[ChatResponseData])
@limiter.limit(settings.rate_limit_default)
async def chat(request: Request, payload: ChatRequest, subject: str = Depends(get_current_subject)):
    session_id = payload.session_id or str(uuid.uuid4())
    db = get_db()

    result = run_chat_pipeline(payload.message)

    await append_message(db, session_id, subject, Message(role="user", content=payload.message))
    await append_message(
        db, session_id, subject,
        Message(role="assistant", content=result.reply_text, routed_agents=result.routed_agents),
    )

    return APIResponse(
        success=True,
        data=ChatResponseData(reply=result.reply_text, routed_agents=result.routed_agents, session_id=session_id),
    )


@router_.get("/history/{session_id}", response_model=APIResponse[ConversationHistoryData])
async def chat_history(
    session_id: str = Path(pattern=SESSION_ID_PATTERN),
    subject: str = Depends(get_current_subject),
):
    db = get_db()
    messages = await get_history(db, session_id, subject)
    if messages is None:
        # Same response whether the session doesn't exist or belongs to someone
        # else — never reveals which, to avoid leaking session existence (Instruction 7).
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    return APIResponse(success=True, data=ConversationHistoryData(session_id=session_id, messages=messages))


@router_.get("/sessions", response_model=APIResponse[SessionListData])
async def chat_sessions(subject: str = Depends(get_current_subject)):
    """Lists the current user's past conversations, most recently active first."""
    db = get_db()
    sessions = await list_sessions(db, subject)
    return APIResponse(success=True, data=SessionListData(sessions=sessions))
