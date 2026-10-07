"""데이터 CRUD + 요약(summary) 계산. 요약 규칙은 M-1 `src/analyze.py` recent_trend와 동일(최근 7일 vs 직전 7일, ±5%)."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.models.data import DataIn, DataUpdate
from app.repositories import get_repository

COLLECTION = "data"
TREND_BAND = 0.05


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def list_data(limit: int | None = None, order: str = "asc") -> list[dict]:
    return get_repository().list(COLLECTION, order_by="date", descending=(order == "desc"), limit=limit)


def get_data(doc_id: str) -> dict:
    doc = get_repository().get(COLLECTION, doc_id)
    if not doc:
        raise NotFoundError(f"데이터 {doc_id} 를 찾을 수 없습니다.")
    return doc


def create_data(payload: DataIn) -> dict:
    now = _now()
    return get_repository().create(COLLECTION, {**payload.model_dump(), "created_at": now, "updated_at": now})


def update_data(doc_id: str, payload: DataUpdate) -> dict:
    patch = {k: v for k, v in payload.model_dump().items() if v is not None}
    patch["updated_at"] = _now()
    doc = get_repository().update(COLLECTION, doc_id, patch)
    if not doc:
        raise NotFoundError(f"데이터 {doc_id} 를 찾을 수 없습니다.")
    return doc


def delete_data(doc_id: str) -> None:
    if not get_repository().delete(COLLECTION, doc_id):
        raise NotFoundError(f"데이터 {doc_id} 를 찾을 수 없습니다.")


def compute_summary(records: list[dict]) -> dict:
    """레코드 목록 → summary dict. 날짜 오름차순으로 정렬해 계산한다."""
    rows = sorted((r for r in records if r.get("date") is not None and r.get("value") is not None), key=lambda r: r["date"])
    base = {"label": settings.data_label, "unit": settings.unit}
    if not rows:
        return {**base, "period": {"start": None, "end": None}, "count": 0, "metrics": None, "recent_7_days": None,
                "trend": "not_enough_data", "trend_change_pct": None, "top_memo": None, "latest": None}

    values = [float(r["value"]) for r in rows]
    last7 = values[-7:]
    prev7 = values[-14:-7]
    if len(values) >= 14:
        recent, previous = sum(last7) / 7, sum(prev7) / 7
        change = (recent / previous - 1) if previous else 0.0
        trend = "increasing" if change > TREND_BAND else "decreasing" if change < -TREND_BAND else "stable"
        change_pct = round(change * 100, 1)
    else:
        trend, change_pct = "not_enough_data", None

    memos = Counter(str(r.get("memo", "")).strip() for r in rows if str(r.get("memo", "")).strip())
    latest = rows[-1]
    return {
        **base,
        "period": {"start": rows[0]["date"], "end": latest["date"]},
        "count": len(rows),
        "metrics": {"total": round(sum(values), 1), "average": round(sum(values) / len(values), 1),
                    "max": round(max(values), 1), "min": round(min(values), 1)},
        "recent_7_days": {"total": round(sum(last7), 1), "average": round(sum(last7) / len(last7), 1), "count": len(last7)},
        "trend": trend,
        "trend_change_pct": change_pct,
        "top_memo": memos.most_common(1)[0][0] if memos else None,
        "latest": {"date": latest["date"], "value": latest["value"], "memo": latest.get("memo", "")},
    }


def get_summary() -> dict:
    return compute_summary(list_data())


def summary_to_text(s: dict) -> str:
    """시스템 프롬프트에 넣는 요약 문장. 숫자는 요약에 있는 것만."""
    if s["count"] == 0:
        return f"[사용자 데이터 요약] 저장된 {s['label']} 데이터가 없습니다. 데이터가 없다고 안내하세요."
    m, r7 = s["metrics"], s["recent_7_days"]
    trend_ko = {"increasing": "증가", "decreasing": "감소", "stable": "유지", "not_enough_data": "판단 불가(14일 미만)"}[s["trend"]]
    lines = [
        f"[사용자 데이터 요약] {s['label']} (단위 {s['unit']})",
        f"- 기간: {s['period']['start']} ~ {s['period']['end']}, 레코드 {s['count']}개",
        f"- 전체: 합계 {m['total']:,}, 평균 {m['average']:,}, 최대 {m['max']:,}, 최소 {m['min']:,}",
        f"- 최근 7일: 합계 {r7['total']:,}, 평균 {r7['average']:,}",
        f"- 추세: {trend_ko}" + (f" (최근 7일 평균이 직전 7일 대비 {s['trend_change_pct']:+.1f}%)" if s["trend_change_pct"] is not None else ""),
        f"- 마지막 기록: {s['latest']['date']} {s['latest']['value']:,} {s['unit']}" + (f" ({s['latest']['memo']})" if s["latest"].get("memo") else ""),
    ]
    if s.get("top_memo"):
        lines.append(f"- 가장 많은 메모: {s['top_memo']}")
    return "\n".join(lines)
