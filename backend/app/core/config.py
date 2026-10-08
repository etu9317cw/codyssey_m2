"""환경변수 설정. 미션 예시 이름(OPENAI_*)과 기존 과제 이름(CODYSSEY_*)을 둘 다 읽는다."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_DIR / ".env")


def _first(*names: str, default: str = "") -> str:
    for n in names:
        v = os.environ.get(n)
        if v:
            return v.strip()
    return default


def _base_url() -> str | None:
    """LLM 주소. 비어 있으면 None → openai SDK 기본(OpenAI 공식 API). 프록시 주소에 '/v1'이 없으면 붙인다."""
    raw = _first("OPENAI_BASE_URL", "CODYSSEY_BASE_URL").rstrip("/")
    if not raw:
        return None
    return raw if raw.endswith("/v1") else raw + "/v1"


@dataclass
class Settings:
    app_name: str = "센터 운영 비서 API"
    storage: str = field(default_factory=lambda: _first("STORAGE", default="memory").lower())  # memory | firestore
    memory_file: Path = field(default_factory=lambda: Path(_first("MEMORY_FILE", default=str(BACKEND_DIR / "data" / "store.local.json"))))

    llm_api_key: str = field(default_factory=lambda: _first("OPENAI_API_KEY", "CODYSSEY_API_KEY"))
    llm_base_url: str | None = field(default_factory=_base_url)   # None 이면 OpenAI 기본
    llm_model: str = field(default_factory=lambda: _first("LLM_MODEL", "CODYSSEY_MODEL", default="gemini-3-flash"))
    llm_timeout: float = field(default_factory=lambda: float(_first("LLM_TIMEOUT", default="20")))

    firebase_service_account_json: str = field(default_factory=lambda: _first("FIREBASE_SERVICE_ACCOUNT_JSON"))
    firebase_project_id: str = field(default_factory=lambda: _first("FIREBASE_PROJECT_ID"))
    firebase_client_email: str = field(default_factory=lambda: _first("FIREBASE_CLIENT_EMAIL"))
    firebase_private_key: str = field(default_factory=lambda: _first("FIREBASE_PRIVATE_KEY"))

    allowed_origins: list[str] = field(default_factory=lambda: [o.strip() for o in _first("ALLOWED_ORIGINS", default="http://localhost:5500,http://127.0.0.1:5500").split(",") if o.strip()])
    unit: str = field(default_factory=lambda: _first("DATA_UNIT", default="kWh"))
    data_label: str = field(default_factory=lambda: _first("DATA_LABEL", default="센터 교육동 일별 전력 사용량"))

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key)

    @property
    def firebase_configured(self) -> bool:
        return bool(self.firebase_service_account_json) or bool(self.firebase_project_id and self.firebase_client_email and self.firebase_private_key)


settings = Settings()
