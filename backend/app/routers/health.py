from fastapi import APIRouter

from app.core.config import settings
from app.repositories import storage_kind

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", summary="서버 상태")
def health():
    return {"status": "ok", "storage": storage_kind(), "llm_configured": settings.llm_configured,
            "model": settings.llm_model, "label": settings.data_label, "unit": settings.unit}
