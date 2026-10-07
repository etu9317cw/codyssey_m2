"""챗 요청·응답 모델."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, examples=["지난주 사용량이 늘었나요?"])
    conversation_id: Optional[str] = Field(None, description="이어서 대화할 때. 없으면 새 대화 생성")

    @field_validator("message")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("메시지를 입력하세요")
        return v


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    summary_used: dict
    model: str
