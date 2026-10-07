"""Firebase Admin 지연 초기화. 서비스 계정 키는 JSON 문자열/파일 경로 또는 3개 환경변수로 받는다."""
from __future__ import annotations

import json
from pathlib import Path

from app.core.config import settings

_client = None


def get_firestore():
    """firestore.Client 를 한 번만 만든다. firebase가 설정되지 않았으면 RuntimeError."""
    global _client
    if _client is not None:
        return _client
    if not settings.firebase_configured:
        raise RuntimeError("Firebase 환경변수가 없습니다 (FIREBASE_SERVICE_ACCOUNT_JSON 또는 PROJECT_ID/CLIENT_EMAIL/PRIVATE_KEY)")

    import firebase_admin
    from firebase_admin import credentials, firestore

    if settings.firebase_service_account_json:
        raw = settings.firebase_service_account_json
        info = json.loads(Path(raw).read_text(encoding="utf-8")) if Path(raw).exists() else json.loads(raw)
    else:
        info = {
            "type": "service_account",
            "project_id": settings.firebase_project_id,
            "client_email": settings.firebase_client_email,
            "private_key": settings.firebase_private_key.replace("\\n", "\n"),
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(info))
    _client = firestore.client()
    return _client
