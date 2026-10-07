"""센터 운영 비서 API — FastAPI 앱 진입점.

실행: uvicorn main:app --reload --port 8000   (Swagger: http://localhost:8000/docs)
구조: routers(경로·상태코드) → services(비즈니스·LLM) → repositories(memory|firestore) → core(설정·예외·Firebase)
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.routers import chat, conversations, data, health

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "시계열 데이터(센터 교육동 일별 전력 사용량)를 저장하고, 그 요약을 시스템 프롬프트에 주입해 대화하는 AI 비서 API.\n\n"
        "- `GET /api/data/summary` 가 돌려주는 요약이 `POST /api/chat` 의 컨텍스트로 그대로 들어간다.\n"
        "- 대화는 `/api/chat` 이 자동 저장한다 (프론트는 따로 저장하지 않음).\n"
        "- 저장소: `STORAGE=memory`(기본, JSON 파일) 또는 `firestore`."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(health.router)
app.include_router(data.router)
app.include_router(conversations.router)
app.include_router(chat.router)


@app.get("/", include_in_schema=False)
def root():
    return {"name": settings.app_name, "docs": "/docs", "health": "/api/health"}
