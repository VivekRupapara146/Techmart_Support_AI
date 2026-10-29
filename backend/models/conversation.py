"""
Conversation/session schemas.
"""
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    routed_agents: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Real, measured telemetry for assistant messages only (None for "user"
    # messages, and for anything persisted before this field existed — old
    # documents decode fine, these three just come back None). Lets the
    # versioned /v1/chat endpoint report a real running cost per session
    # instead of a per-request-only number that resets on every turn.
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: float | None = None


class SessionSummary(BaseModel):
    session_id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    preview: str = ""


class SessionListData(BaseModel):
    sessions: list[SessionSummary]


class ConversationHistoryData(BaseModel):
    session_id: str
    messages: list[Message]
