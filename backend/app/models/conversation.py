"""대화 모델. 문서 1개 = 대화 1건, messages 배열에 user/assistant 턴이 누적된다."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)
    created_at: str


class ConversationCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=60, description="비우면 첫 질문 앞 30자")
    messages: list[Message] = Field(default_factory=list, description="프론트가 직접 저장할 때만 사용. 보통은 /api/chat 이 자동 저장")


class ConversationListItem(BaseModel):
    id: str
    title: str
    message_count: int
    created_at: str
    updated_at: str
    preview: str = ""


class ConversationOut(ConversationListItem):
    messages: list[Message]
