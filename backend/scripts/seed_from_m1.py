"""M-1 데이터를 비서 DB에 적재한다.

사용: python scripts/seed_from_m1.py [--csv ../../M-1_시계열분석/data/sample/electricity_daily.csv] [--days 120] [--reset]
- 기본: M-1 시뮬레이션 CSV의 최근 120일을 data 컬렉션에 넣는다 (memo 포함)
- --reset: 기존 data 컬렉션을 비우고 넣는다
- STORAGE 설정(memory/firestore)을 그대로 따른다
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.models.data import DataIn  # noqa: E402
from app.services import data_service  # noqa: E402

DEFAULT_CSV = BACKEND.parents[1] / "M-1_시계열분석" / "data" / "sample" / "electricity_daily.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", default=str(DEFAULT_CSV))
    parser.add_argument("--days", type=int, default=120)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    path = Path(args.csv)
    if not path.exists():
        sys.exit(f"CSV가 없습니다: {path}")

    with open(path, encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f)]
    rows = [r for r in rows if r.get("date") and r.get("value")]
    rows = rows[-args.days:]

    if args.reset:
        existing = data_service.list_data()
        for d in existing:
            data_service.delete_data(d["id"])
        print(f"기존 {len(existing)}건 삭제")

    for r in rows:
        memo = (r.get("memo") or "").replace("(이상치)", "").strip()
        data_service.create_data(DataIn(date=r["date"], value=float(r["value"]), memo=memo[:200]))

    s = data_service.get_summary()
    print(f"{len(rows)}건 적재 → 총 {s['count']}건, 기간 {s['period']['start']} ~ {s['period']['end']}, "
          f"평균 {s['metrics']['average']:,} {s['unit']}, 추세 {s['trend']} ({s['trend_change_pct']}%)")


if __name__ == "__main__":
    main()
