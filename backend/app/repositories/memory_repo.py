"""인메모리 저장소 + JSON 파일 영속. Firebase 키가 없어도 서비스 전체가 동작하게 한다 (로컬 개발·테스트·채점자 실행용)."""
from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Optional

from app.repositories.base import Repository


class MemoryRepository(Repository):
    def __init__(self, file: Optional[Path] = None):
        self._file = file
        self._lock = threading.Lock()
        self._store: dict[str, dict[str, dict]] = {"data": {}, "conversations": {}}
        if file and file.exists():
            try:
                loaded = json.loads(file.read_text(encoding="utf-8"))
                for col in self._store:
                    self._store[col] = loaded.get(col, {})
            except (OSError, json.JSONDecodeError):
                pass  # 손상된 파일은 무시하고 빈 저장소로 시작

    def _flush(self) -> None:
        if not self._file:
            return
        self._file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._store, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self._file)

    def _col(self, collection: str) -> dict[str, dict]:
        return self._store.setdefault(collection, {})

    def list(self, collection, order_by="date", descending=False, limit=None):
        with self._lock:
            docs = [dict(d, id=i) for i, d in self._col(collection).items()]
        docs.sort(key=lambda d: (d.get(order_by) is None, d.get(order_by, "")), reverse=descending)
        return docs[:limit] if limit else docs

    def get(self, collection, doc_id):
        with self._lock:
            d = self._col(collection).get(doc_id)
            return dict(d, id=doc_id) if d else None

    def create(self, collection, doc):
        doc_id = doc.pop("id", None) or uuid.uuid4().hex[:20]
        with self._lock:
            self._col(collection)[doc_id] = dict(doc)
            self._flush()
        return dict(doc, id=doc_id)

    def update(self, collection, doc_id, patch):
        with self._lock:
            col = self._col(collection)
            if doc_id not in col:
                return None
            col[doc_id].update({k: v for k, v in patch.items() if k != "id"})
            self._flush()
            return dict(col[doc_id], id=doc_id)

    def delete(self, collection, doc_id):
        with self._lock:
            removed = self._col(collection).pop(doc_id, None) is not None
            if removed:
                self._flush()
            return removed

    def count(self, collection):
        with self._lock:
            return len(self._col(collection))
