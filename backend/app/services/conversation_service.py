"""대화 CRUD. 문서 1개 = 대화 1건, messages 배열 누적."""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.exceptions import NotFoundError
from app.models.conversation import ConversationCreate
from app.repositories import get_repository

COLLECTION = "conversations"
TITLE_LEN = 30


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _title_from(messages: list[dict], fallback: str = "새 대화") -> str:
    for m in messages:
        if m.get("role") == "user" and m.get("content"):
            text = " ".join(m["content"].split())
            return text[:TITLE_LEN] + ("…" if len(text) > TITLE_LEN else "")
    return fallback


def _to_item(doc: dict, with_messages: bool) -> dict:
    messages = doc.get("messages", [])
    last = messages[-1]["content"] if messages else ""
    item = {"id": doc["id"], "title": doc.get("title", ""), "message_count": len(messages),
            "created_at": doc.get("created_at", ""), "updated_at": doc.get("updated_at", ""),
            "preview": (last[:60] + "…") if len(last) > 60 else last}
    if with_messages:
        item["messages"] = messages
    return item


def list_conversations(limit: int | None = None) -> list[dict]:
    docs = get_repository().list(COLLECTION, order_by="updated_at", descending=True, limit=limit)
    return [_to_item(d, with_messages=False) for d in docs]


def get_conversation(conv_id: str) -> dict:
    doc = get_repository().get(COLLECTION, conv_id)
    if not doc:
        raise NotFoundError(f"대화 {conv_id} 를 찾을 수 없습니다.")
    return _to_item(doc, with_messages=True)


def create_conversation(payload: ConversationCreate | None = None) -> dict:
    now = _now()
    messages = [m.model_dump() for m in (payload.messages if payload else [])]
    title = (payload.title.strip() if payload and payload.title else "") or _title_from(messages)
    doc = get_repository().create(COLLECTION, {"title": title, "messages": messages, "created_at": now, "updated_at": now})
    return _to_item(doc, with_messages=True)


def append_messages(conv_id: str, new_messages: list[dict]) -> dict:
    repo = get_repository()
    doc = repo.get(COLLECTION, conv_id)
    if not doc:
        raise NotFoundError(f"대화 {conv_id} 를 찾을 수 없습니다.")
    messages = list(doc.get("messages", [])) + new_messages
    patch = {"messages": messages, "updated_at": _now()}
    if not doc.get("title") or doc.get("title") == "새 대화":
        patch["title"] = _title_from(messages)
    updated = repo.update(COLLECTION, conv_id, patch)
    return _to_item(updated, with_messages=True)


def delete_conversation(conv_id: str) -> None:
    if not get_repository().delete(COLLECTION, conv_id):
        raise NotFoundError(f"대화 {conv_id} 를 찾을 수 없습니다.")


def now_iso() -> str:
    return _now()
