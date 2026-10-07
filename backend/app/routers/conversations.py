"""대화 API. (A) 방식: 목록은 요약만, GET /{id} 로 메시지 전체를 불러온다."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query, Response, status

from app.models.conversation import ConversationCreate, ConversationListItem, ConversationOut
from app.services import conversation_service

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationListItem], summary="대화 목록 (최근 수정순)")
def list_conversations(limit: Optional[int] = Query(None, ge=1, le=200)):
    return conversation_service.list_conversations(limit=limit)


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED,
             summary="대화 생성 (보통은 /api/chat 이 자동 생성)")
def create(payload: ConversationCreate | None = None):
    return conversation_service.create_conversation(payload)


@router.get("/{conv_id}", response_model=ConversationOut, summary="대화 불러오기 (메시지 포함)")
def get_one(conv_id: str):
    return conversation_service.get_conversation(conv_id)


@router.delete("/{conv_id}", status_code=status.HTTP_204_NO_CONTENT, summary="대화 삭제")
def delete(conv_id: str):
    conversation_service.delete_conversation(conv_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
