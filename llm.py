"""Same LLM helper as Projects 1–3. Nothing new."""
import os
from typing import Type, TypeVar
from pydantic import BaseModel
from openai import OpenAI

T = TypeVar("T", bound=BaseModel)
MODEL = os.getenv("LLM_MODEL", "gpt-5.4-mini")

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def call_llm(prompt: str, schema: Type[T], system: str, temperature: float = 0.2) -> T:
    response = _get_client().chat.completions.parse(
        model=MODEL,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        response_format=schema,
    )
    parsed = response.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError(f"Model refused: {response.choices[0].message.refusal}")
    return parsed
