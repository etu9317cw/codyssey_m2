"""챗: summary 조회 → 시스템 프롬프트에 주입(컨텍스트 주입) → LLM → conversations 자동 저장.

프론트는 /api/chat 만 호출한다. 저장은 여기서 한 번만 하므로 중복 저장이 생기지 않는다.
"""
from __future__ import annotations

from app.core.config import settings
from app.models.chat import ChatRequest
from app.services import conversation_service, data_service, llm_client

HISTORY_TURNS = 6   # 이전 대화 중 LLM에 넘기는 최근 메시지 수(토큰 절약)

ROLE_RULES = """당신은 대학교 에너지인력양성센터의 "센터 운영 비서"입니다. 센터 담당자의 질문에 아래 데이터 요약을 근거로 답합니다.

[규칙]
1. 수치는 요약에 있는 것만 말합니다. 요약에 없는 날짜·값·금액은 만들어 내지 않고 "요약에 없는 정보"라고 말합니다.
2. 추세를 말할 때는 어떤 비교(최근 7일 vs 직전 7일)인지 함께 말하고, 공휴일·방학이 끼어 있을 수 있음을 한 줄 덧붙입니다.
3. 간결한 존댓말, 불릿 2~5개 이내. 인사말·이모지 금지. 실명 대신 역할명만 씁니다.
4. 센터 운영·에너지 데이터와 무관한 질문이면 "센터 운영 비서 범위 밖"이라고 짧게 답합니다.
5. 데이터가 없으면 데이터 관리에서 먼저 추가하라고 안내합니다."""

SHORT_RULES = "당신은 센터 운영 비서입니다. 아래 데이터 요약에 있는 수치만 근거로 간결한 존댓말로 답하고, 없는 정보는 없다고 말합니다."


def build_system_prompt(summary: dict, short: bool = False) -> str:
    return f"{SHORT_RULES if short else ROLE_RULES}\n\n{data_service.summary_to_text(summary)}"


def chat(req: ChatRequest) -> dict:
    summary = data_service.get_summary()

    history: list[dict] = []
    if req.conversation_id:
        conv = conversation_service.get_conversation(req.conversation_id)   # 없으면 404
        history = [{"role": m["role"], "content": m["content"]} for m in conv["messages"][-HISTORY_TURNS:]]

    messages = history + [{"role": "user", "content": req.message}]
    answer, model = llm_client.complete(build_system_prompt(summary), messages, build_system_prompt(summary, short=True))

    # LLM이 성공한 뒤에만 저장한다 → 실패 시 빈 대화가 남지 않는다
    now = conversation_service.now_iso()
    new_messages = [
        {"role": "user", "content": req.message, "created_at": now},
        {"role": "assistant", "content": answer, "created_at": now},
    ]
    if req.conversation_id:
        conv = conversation_service.append_messages(req.conversation_id, new_messages)
    else:
        from app.models.conversation import ConversationCreate, Message
        conv = conversation_service.create_conversation(ConversationCreate(messages=[Message(**m) for m in new_messages]))
    return {"conversation_id": conv["id"], "answer": answer, "summary_used": summary, "model": model}
