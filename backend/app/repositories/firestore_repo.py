"""Firestore 저장소 (firebase-admin). 컬렉션 "data", "conversations"."""
from __future__ import annotations

from typing import Optional

from app.repositories.base import Repository


class FirestoreRepository(Repository):
    def __init__(self, client=None):
        if client is None:
            from app.core.firebase import get_firestore
            client = get_firestore()
        self._db = client

    def list(self, collection, order_by="date", descending=False, limit=None):
        from google.cloud.firestore_v1 import Query
        q = self._db.collection(collection).order_by(order_by, direction=Query.DESCENDING if descending else Query.ASCENDING)
        if limit:
            q = q.limit(limit)
        return [dict(snap.to_dict(), id=snap.id) for snap in q.stream()]

    def get(self, collection, doc_id):
        snap = self._db.collection(collection).document(doc_id).get()
        return dict(snap.to_dict(), id=snap.id) if snap.exists else None

    def create(self, collection, doc):
        doc = dict(doc)
        doc_id = doc.pop("id", None)
        ref = self._db.collection(collection).document(doc_id) if doc_id else self._db.collection(collection).document()
        ref.set(doc)
        return dict(doc, id=ref.id)

    def update(self, collection, doc_id, patch):
        ref = self._db.collection(collection).document(doc_id)
        if not ref.get().exists:
            return None
        ref.update({k: v for k, v in patch.items() if k != "id"})
        snap = ref.get()
        return dict(snap.to_dict(), id=snap.id)

    def delete(self, collection, doc_id):
        ref = self._db.collection(collection).document(doc_id)
        if not ref.get().exists:
            return False
        ref.delete()
        return True

    def count(self, collection):
        agg = self._db.collection(collection).count().get()
        return int(agg[0][0].value)
