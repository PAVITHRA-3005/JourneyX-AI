from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from journeyx.config.capstone import build_http_client, get_settings

T = TypeVar("T", bound=BaseModel)


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_in: int | None
    tokens_out: int | None
    latency_ms: float
    raw: dict[str, Any]


class LLMClient:
    """OpenAI-compatible chat client with CA trust, retries, and JSON validation."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_s: float | None = None,
        max_retries: int = 2,
    ) -> None:
        settings = get_settings().chat
        self.base_url = (base_url or settings.api_base).rstrip("/")
        self.api_key = api_key or settings.api_key
        self.model = model or settings.model
        self.timeout_s = timeout_s or settings.timeout_s
        self.max_tokens = settings.max_tokens
        self.verify = settings.verify
        self.max_retries = max_retries
        self.dry_run = os.getenv("JOURNEYX_BASELINE_DRY_RUN", "").lower() in ("1", "true", "yes")

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key) and not self.dry_run

    def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.2,
        response_format: dict[str, Any] | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        if self.dry_run or not self.configured:
            return LLMResponse(
                content="{}",
                model=self.model or "dry-run",
                tokens_in=0,
                tokens_out=0,
                latency_ms=0.0,
                raw={"dry_run": True},
            )

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"{self.base_url}/chat/completions"
        start = time.perf_counter()
        last_exc: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                with build_http_client(get_settings().chat) as client:
                    resp = client.post(url, json=payload, headers=headers)
                    if resp.status_code in (429, 503) and attempt < self.max_retries:
                        time.sleep(2**attempt)
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                break
            except (httpx.HTTPError, httpx.ConnectError) as exc:
                last_exc = exc
                if attempt >= self.max_retries:
                    raise
                time.sleep(2**attempt)
        else:
            if last_exc:
                raise last_exc
            raise RuntimeError("chat request failed")

        latency_ms = (time.perf_counter() - start) * 1000
        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage") or {}
        return LLMResponse(
            content=choice or "",
            model=data.get("model", self.model),
            tokens_in=usage.get("prompt_tokens"),
            tokens_out=usage.get("completion_tokens"),
            latency_ms=latency_ms,
            raw=data,
        )

    def chat_structured(
        self,
        messages: list[ChatMessage],
        schema_model: type[T],
        temperature: float = 0.1,
    ) -> tuple[T | None, LLMResponse, list[str]]:
        """Constrained JSON → Pydantic with retries. No response_format for compatibility."""
        errors: list[str] = []
        last_response: LLMResponse | None = None

        # Inject JSON instruction into system message instead of using response_format
        schema_str = json.dumps(schema_model.model_json_schema(), indent=2)
        json_instruction = ChatMessage(
            role="system",
            content=(
                f"You MUST respond with valid JSON only — no markdown, no explanation, no code fences. "
                f"Return a single JSON object matching this schema:\n{schema_str}"
            ),
        )
        attempt_messages = [json_instruction] + list(messages)

        for attempt in range(self.max_retries + 1):
            try:
                last_response = self.chat(
                    attempt_messages,
                    temperature=temperature,
                    # No response_format — not supported by all models
                )
                # Strip markdown code fences if present
                content = last_response.content.strip()
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.strip()
                parsed = json.loads(content)
                model = schema_model.model_validate(parsed)
                return model, last_response, errors
            except (json.JSONDecodeError, ValidationError, KeyError) as exc:
                err = f"attempt {attempt + 1}: {exc}"
                errors.append(err)
                attempt_messages = attempt_messages + [
                    ChatMessage(
                        role="user",
                        content=(
                            f"Your JSON was invalid. Return ONLY valid JSON, no markdown. Error: {exc}"
                        ),
                    )
                ]

        assert last_response is not None
        return None, last_response, errors
