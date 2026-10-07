"""저장소 인터페이스. 서비스 계층은 이 메서드만 쓰고, 구현(memory/firestore)은 설정으로 고른다.

컬렉션은 두 개: "data"(시계열 레코드), "conversations"(대화). 문서는 dict, id는 문자열.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class Repository(ABC):
    @abstractmethod
    def list(self, collection: str, order_by: str = "date", descending: bool = False, limit: Optional[int] = None) -> list[dict]: ...

    @abstractmethod
    def get(self, collection: str, doc_id: str) -> Optional[dict]: ...

    @abstractmethod
    def create(self, collection: str, doc: dict) -> dict: ...

    @abstractmethod
    def update(self, collection: str, doc_id: str, patch: dict) -> Optional[dict]: ...

    @abstractmethod
    def delete(self, collection: str, doc_id: str) -> bool: ...

    @abstractmethod
    def count(self, collection: str) -> int: ...
