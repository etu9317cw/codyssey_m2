"""설정(STORAGE)에 따라 저장소 구현을 고른다. Firebase 설정이 없으면 memory로 자동 전환."""
from __future__ import annotations

from app.core.config import settings
from app.repositories.base import Repository
from app.repositories.memory_repo import MemoryRepository

_repo: Repository | None = None


def get_repository() -> Repository:
    global _repo
    if _repo is None:
        if settings.storage == "firestore" and settings.firebase_configured:
            from app.repositories.firestore_repo import FirestoreRepository
            _repo = FirestoreRepository()
        else:
            _repo = MemoryRepository(settings.memory_file)
    return _repo


def set_repository(repo: Repository | None) -> None:
    """테스트에서 교체용."""
    global _repo
    _repo = repo


def storage_kind() -> str:
    repo = get_repository()
    return "firestore" if repo.__class__.__name__ == "FirestoreRepository" else "memory"
