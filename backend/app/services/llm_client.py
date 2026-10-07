"""LLM 호출. 기관 프록시(OpenAI 호환)를 openai SDK의 base_url 교체로 쓴다.

- max_tokens 생략 (gemini-3-flash는 사고 토큰이 상한에 포함되어 본문이 잘릴 수 있음, A-2·A-3에서 확인)
- 400(Invalid request)이면 시스템 프롬프트를 줄여 1회 재시도 (프록시가 긴 프롬프트에서 간헐적으로 거부)
- 키가 없으면 LLMNotConfiguredError(503) → 프론트가 "LLM 미설정" 안내
"""
from __future__ import annotations

from app.core.config import settings
from app.core.exceptions import LLMNotConfiguredError, UpstreamError

_client = None


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url, timeout=settings.llm_timeout, max_retries=0)
    return _client


def complete(system_prompt: str, messages: list[dict], short_system_prompt: str | None = None) -> tuple[str, str]:
    """(답변 텍스트, 모델 이름). messages는 [{role, content}] (user/assistant)."""
    if not settings.llm_configured:
        raise LLMNotConfiguredError("LLM API 키가 설정되지 않았습니다. 서버 환경변수 OPENAI_API_KEY(또는 CODYSSEY_API_KEY)를 등록하세요.")

    from openai import APIConnectionError, APIStatusError, APITimeoutError

    client = _get_client()
    attempts = [system_prompt] + ([short_system_prompt] if short_system_prompt else [])
    last_error = "알 수 없는 오류"
    for i, sp in enumerate(attempts):
        try:
            res = client.chat.completions.create(
                model=settings.llm_model,
                messages=[{"role": "system", "content": sp}] + [{"role": m["role"], "content": m["content"]} for m in messages],
            )
            text = (res.choices[0].message.content or "").strip()
            if not text:
                last_error = "모델이 빈 응답을 돌려주었습니다"
                continue
            return text, res.model or settings.llm_model
        except APITimeoutError:
            raise UpstreamError("AI 응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.")
        except APIConnectionError:
            raise UpstreamError("AI 서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.")
        except APIStatusError as e:
            last_error = f"LLM HTTP {e.status_code}"
            if e.status_code == 400 and i + 1 < len(attempts):
                continue   # 짧은 프롬프트로 재시도
            if e.status_code in (401, 403):
                raise UpstreamError("AI API 키가 거부되었습니다. 서버 환경변수를 확인하세요.")
            raise UpstreamError(f"AI 서버 오류({e.status_code}). 잠시 후 다시 시도해 주세요.")
    raise UpstreamError(f"AI 응답을 받지 못했습니다 ({last_error}).")
