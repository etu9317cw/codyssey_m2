"""데이터 API 5개. /summary 는 /{id} 보다 먼저 등록해야 'summary'가 id로 해석되지 않는다."""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Query, Response, status

from app.models.data import DataIn, DataOut, DataUpdate, Summary
from app.services import data_service

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/summary", response_model=Summary, summary="데이터 요약 (챗봇 컨텍스트와 동일)")
def summary():
    return data_service.get_summary()


@router.get("", response_model=list[DataOut], summary="데이터 목록")
def list_data(limit: Optional[int] = Query(None, ge=1, le=1000), order: Literal["asc", "desc"] = "asc"):
    return data_service.list_data(limit=limit, order=order)


@router.post("", response_model=DataOut, status_code=status.HTTP_201_CREATED, summary="데이터 추가")
def create(payload: DataIn):
    return data_service.create_data(payload)


@router.get("/{doc_id}", response_model=DataOut, summary="데이터 1건")
def get_one(doc_id: str):
    return data_service.get_data(doc_id)


@router.put("/{doc_id}", response_model=DataOut, summary="데이터 수정 (일부 필드 가능)")
def update(doc_id: str, payload: DataUpdate):
    return data_service.update_data(doc_id, payload)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT, summary="데이터 삭제")
def delete(doc_id: str):
    data_service.delete_data(doc_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
