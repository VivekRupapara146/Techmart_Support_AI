"""
Conversation storage: one document per session_id, embedded messages array.

Security: every read/write filters on {session_id, owner} together, so a
user can never read or append to a session_id that isn't theirs, even if
they guess a valid one (least privilege / Instruction 7).

Scalability: message array is capped at MAX_MESSAGES_PER_SESSION via
$slice, so a very long-running session can't grow the document unbounded
(Instruction 10).
"""
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from models.conversation import Message
from core.logging import get_logger

logger = get_logger(__name__)

COLLECTION = "conversations"
MAX_MESSAGES_PER_SESSION = 50


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db[COLLECTION].create_index([("session_id", 1), ("owner", 1)], unique=True)
    await db[COLLECTION].create_index([("owner", 1), ("updated_at", -1)])


async def append_message(db: AsyncIOMotorDatabase, session_id: str, owner: str, message: Message) -> None:
    now = datetime.now(timezone.utc)
    await db[COLLECTION].update_one(
        {"session_id": session_id, "owner": owner},
        {
            "$push": {"messages": {"$each": [message.model_dump()], "$slice": -MAX_MESSAGES_PER_SESSION}},
            "$set": {"updated_at": now},
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )


async def get_history(db: AsyncIOMotorDatabase, session_id: str, owner: str) -> list[Message] | None:
    """Returns None if the session doesn't exist OR doesn't belong to this owner —
    callers should treat both cases identically (404), never revealing which."""
    doc = await db[COLLECTION].find_one({"session_id": session_id, "owner": owner})
    if doc is None:
        return None
    return [Message(**m) for m in doc.get("messages", [])]


async def list_sessions(db: AsyncIOMotorDatabase, owner: str, limit: int = 30) -> list[dict]:
    """
    Returns session summaries for a user, most-recently-active first.
    Each summary is deliberately lightweight (no full message history) —
    the frontend fetches full history separately per-session via
    get_history, only when a specific session is opened.
    """
    cursor = (
        db[COLLECTION]
        .find(
            {"owner": owner},
            {"session_id": 1, "created_at": 1, "updated_at": 1, "messages": {"$slice": -1}},
        )
        .sort("updated_at", -1)
        .limit(limit)
    )

    summaries = []
    async for doc in cursor:
        last_messages = doc.get("messages", [])
        preview = last_messages[0]["content"][:80] if last_messages else ""
        summaries.append({
            "session_id": doc["session_id"],
            "created_at": doc.get("created_at"),
            "updated_at": doc.get("updated_at"),
            "preview": preview,
        })
    return summaries
