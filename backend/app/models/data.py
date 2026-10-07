"""데이터 레코드 모델: (date, value, memo). Pydantic이 형식·범위를 검증한다."""
from __future__ import annotations

from datetime import date as _date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class DataIn(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD", examples=["2026-09-01"])
    value: float = Field(..., ge=0, description="측정값 (단위는 서버 설정, 기본 kWh)", examples=[1834.5])
    memo: str = Field("", max_length=200, description="메모 (예: 개강 첫 주, 정전)", examples=["개강 첫 주"])

    @field_validator("date")
    @classmethod
    def _valid_date(cls, v: str) -> str:
        try:
            return _date.fromisoformat(v.strip()).isoformat()
        except ValueError as e:
            raise ValueError("날짜는 YYYY-MM-DD 형식이어야 합니다") from e

    @field_validator("memo")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class DataUpdate(BaseModel):
    """PUT: 일부만 보내도 된다."""
    date: Optional[str] = None
    value: Optional[float] = Field(None, ge=0)
    memo: Optional[str] = Field(None, max_length=200)

    @field_validator("date")
    @classmethod
    def _valid_date(cls, v):
        if v is None:
            return v
        try:
            return _date.fromisoformat(v.strip()).isoformat()
        except ValueError as e:
            raise ValueError("날짜는 YYYY-MM-DD 형식이어야 합니다") from e


class DataOut(DataIn):
    id: str
    created_at: str
    updated_at: str


class Metrics(BaseModel):
    total: float
    average: float
    max: float
    min: float


class Recent7Days(BaseModel):
    total: float
    average: float
    count: int


class Summary(BaseModel):
    label: str
    unit: str
    period: dict               # {"start": "...", "end": "..."}
    count: int
    metrics: Optional[Metrics]
    recent_7_days: Optional[Recent7Days]
    trend: str                 # increasing | decreasing | stable | not_enough_data
    trend_change_pct: Optional[float]
    top_memo: Optional[str]
    latest: Optional[dict]     # 마지막 레코드 {date, value, memo}
