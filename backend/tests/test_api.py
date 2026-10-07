"""API 테스트 — memory 저장소(파일 없음) + LLM mock. 외부 서비스 없이 실행된다."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.repositories import set_repository
from app.repositories.memory_repo import MemoryRepository
from app.services import chat_service, data_service, llm_client
from main import app


@pytest.fixture()
def client(monkeypatch):
    set_repository(MemoryRepository(file=None))          # 테스트마다 빈 저장소
    monkeypatch.setattr(llm_client.settings, "llm_api_key", "test-key")
    yield TestClient(app)
    set_repository(None)


def fake_complete_factory(captured: dict):
    def fake_complete(system_prompt, messages, short_system_prompt=None):
        captured["system_prompt"] = system_prompt
        captured["messages"] = messages
        return "테스트 답변입니다.", "fake-model"
    return fake_complete


def add(client, date, value, memo=""):
    r = client.post("/api/data", json={"date": date, "value": value, "memo": memo})
    assert r.status_code == 201, r.text
    return r.json()


# ---------- health ----------

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["storage"] == "memory"


# ---------- data CRUD ----------

def test_create_and_get_data(client):
    doc = add(client, "2026-09-01", 1834.5, "개강 첫 주")
    assert doc["date"] == "2026-09-01" and doc["memo"] == "개강 첫 주"
    assert client.get(f"/api/data/{doc['id']}").json()["value"] == 1834.5


def test_create_data_validation(client):
    assert client.post("/api/data", json={"date": "2026-13-01", "value": 1}).status_code == 400
    assert client.post("/api/data", json={"date": "2026-09-01", "value": -1}).status_code == 400
    assert client.post("/api/data", json={"date": "2026-09-01"}).status_code == 400
    r = client.post("/api/data", json={"date": "2026-09-01", "value": 1, "memo": "x" * 201})
    assert r.status_code == 400 and r.json()["error"] == "validation_error"


def test_list_order_and_limit(client):
    for d in ("2026-09-03", "2026-09-01", "2026-09-02"):
        add(client, d, 1)
    asc = [x["date"] for x in client.get("/api/data").json()]
    desc = [x["date"] for x in client.get("/api/data?order=desc&limit=2").json()]
    assert asc == ["2026-09-01", "2026-09-02", "2026-09-03"]
    assert desc == ["2026-09-03", "2026-09-02"]


def test_update_partial_and_404(client):
    doc = add(client, "2026-09-01", 100)
    r = client.put(f"/api/data/{doc['id']}", json={"memo": "수정"})
    assert r.status_code == 200 and r.json()["memo"] == "수정" and r.json()["value"] == 100
    assert client.put("/api/data/없음", json={"memo": "x"}).status_code == 404


def test_delete_then_404(client):
    doc = add(client, "2026-09-01", 100)
    assert client.delete(f"/api/data/{doc['id']}").status_code == 204
    assert client.delete(f"/api/data/{doc['id']}").status_code == 404
    assert client.get(f"/api/data/{doc['id']}").json()["error"] == "not_found"


def test_summary_route_not_shadowed_by_id(client):
    """'/api/data/summary' 가 '/api/data/{id}' 로 잡히면 404가 난다."""
    r = client.get("/api/data/summary")
    assert r.status_code == 200 and "trend" in r.json()


# ---------- summary ----------

def test_summary_empty():
    s = data_service.compute_summary([])
    assert s["count"] == 0 and s["trend"] == "not_enough_data" and s["metrics"] is None


def test_summary_metrics_and_trend_increasing():
    rows = [{"date": f"2026-09-{d:02d}", "value": 100.0, "memo": "방학"} for d in range(1, 8)]
    rows += [{"date": f"2026-09-{d:02d}", "value": 120.0, "memo": "학기"} for d in range(8, 15)]
    s = data_service.compute_summary(rows)
    assert s["count"] == 14
    assert s["metrics"]["average"] == 110.0 and s["metrics"]["max"] == 120.0 and s["metrics"]["min"] == 100.0
    assert s["recent_7_days"]["average"] == 120.0
    assert s["trend"] == "increasing" and s["trend_change_pct"] == 20.0
    assert s["period"] == {"start": "2026-09-01", "end": "2026-09-14"}
    assert s["top_memo"] in ("방학", "학기")


def test_summary_trend_stable_and_decreasing():
    base = [{"date": f"2026-09-{d:02d}", "value": 100.0} for d in range(1, 8)]
    stable = base + [{"date": f"2026-09-{d:02d}", "value": 103.0} for d in range(8, 15)]
    down = base + [{"date": f"2026-09-{d:02d}", "value": 80.0} for d in range(8, 15)]
    assert data_service.compute_summary(stable)["trend"] == "stable"
    assert data_service.compute_summary(down)["trend"] == "decreasing"


def test_summary_text_contains_numbers_only_from_summary():
    rows = [{"date": "2026-09-01", "value": 1234.5, "memo": "개강"}]
    text = data_service.summary_to_text(data_service.compute_summary(rows))
    assert "1,234.5" in text and "2026-09-01" in text and "판단 불가" in text


# ---------- conversations ----------

def test_conversation_crud(client):
    r = client.post("/api/conversations", json={"title": "테스트 대화"})
    assert r.status_code == 201
    cid = r.json()["id"]
    assert client.get("/api/conversations").json()[0]["title"] == "테스트 대화"
    got = client.get(f"/api/conversations/{cid}").json()
    assert got["messages"] == [] and got["message_count"] == 0
    assert client.delete(f"/api/conversations/{cid}").status_code == 204
    assert client.get(f"/api/conversations/{cid}").status_code == 404


# ---------- chat ----------

def test_chat_creates_conversation_and_saves_two_messages(client, monkeypatch):
    captured = {}
    monkeypatch.setattr(chat_service.llm_client, "complete", fake_complete_factory(captured))
    for d in range(1, 15):
        add(client, f"2026-09-{d:02d}", 1000 + d * 10)

    r = client.post("/api/chat", json={"message": "최근 추세는?"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["answer"] == "테스트 답변입니다." and body["model"] == "fake-model"
    assert body["summary_used"]["count"] == 14

    conv = client.get(f"/api/conversations/{body['conversation_id']}").json()
    assert conv["message_count"] == 2
    assert [m["role"] for m in conv["messages"]] == ["user", "assistant"]
    assert conv["title"].startswith("최근 추세는?")

    # 컨텍스트 주입: 시스템 프롬프트에 요약 수치가 들어갔는가
    assert "[사용자 데이터 요약]" in captured["system_prompt"]
    assert "레코드 14개" in captured["system_prompt"]
    assert captured["messages"][-1] == {"role": "user", "content": "최근 추세는?"}


def test_chat_continues_conversation_with_history(client, monkeypatch):
    captured = {}
    monkeypatch.setattr(chat_service.llm_client, "complete", fake_complete_factory(captured))
    cid = client.post("/api/chat", json={"message": "첫 질문"}).json()["conversation_id"]
    r = client.post("/api/chat", json={"message": "둘째 질문", "conversation_id": cid})
    assert r.status_code == 200 and r.json()["conversation_id"] == cid
    assert client.get(f"/api/conversations/{cid}").json()["message_count"] == 4
    roles = [m["role"] for m in captured["messages"]]
    assert roles == ["user", "assistant", "user"]          # 이전 2턴 + 새 질문


def test_chat_validation_and_missing_conversation(client, monkeypatch):
    monkeypatch.setattr(chat_service.llm_client, "complete", fake_complete_factory({}))
    assert client.post("/api/chat", json={"message": "   "}).status_code == 400
    assert client.post("/api/chat", json={}).status_code == 400
    assert client.post("/api/chat", json={"message": "x", "conversation_id": "없는대화"}).status_code == 404


def test_chat_without_llm_key_returns_503(client, monkeypatch):
    monkeypatch.setattr(llm_client.settings, "llm_api_key", "")
    r = client.post("/api/chat", json={"message": "안녕"})
    assert r.status_code == 503 and r.json()["error"] == "llm_not_configured"
    assert client.get("/api/conversations").json() == []   # LLM 실패 시 빈 대화를 남기지 않는다


def test_system_prompt_rules_present():
    s = data_service.compute_summary([])
    sp = chat_service.build_system_prompt(s)
    assert "센터 운영 비서" in sp and "요약에 있는 것만" in sp and "데이터가 없습니다" in sp
