from fastapi import APIRouter

from app.models.chat import ChatRequest, ChatResponse
from app.services import chat_service

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse, summary="데이터 요약을 아는 비서와 대화 (대화는 자동 저장)")
def chat(req: ChatRequest):
    return chat_service.chat(req)
