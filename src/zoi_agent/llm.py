from __future__ import annotations

import time
from typing import TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from zoi_agent.config import settings
from zoi_agent.metrics import LLM_LATENCY

T = TypeVar("T", bound=BaseModel)

_client: AsyncOpenAI | None = None


def get_openai() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def parse_structured(
    *,
    model: str,
    schema: type[T],
    system: str,
    user: str,
    component: str = "llm",
    temperature: float = 0.0,
) -> T:
    client = get_openai()
    start = time.perf_counter()
    try:
        resp = await client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format=schema,
            temperature=temperature,
        )
    finally:
        LLM_LATENCY.labels(component=component).observe(time.perf_counter() - start)
    parsed = resp.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError(f"LLM {model} retornou parsed=None (refusal? {resp.choices[0].message.refusal!r})")
    return parsed


async def chat_text(
    *,
    model: str,
    system: str,
    user: str,
    component: str = "llm",
    temperature: float = 0.4,
) -> str:
    client = get_openai()
    start = time.perf_counter()
    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )
    finally:
        LLM_LATENCY.labels(component=component).observe(time.perf_counter() - start)
    return resp.choices[0].message.content or ""
