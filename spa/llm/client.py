"""Provider-agnostic LLM chat-completion client (httpx only)."""
from __future__ import annotations

import os
import time
from typing import Any

import httpx

from spa.audit.logger import AuditLogger
from spa.memory.redaction import redact_text


def llm_enabled() -> bool:
    if os.getenv("SPA_NO_LLM", "").strip().lower() in {"1", "true", "yes"}:
        return False
    return bool(os.getenv("LLM_API_KEY", "").strip())


def _redact_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    return [{"role": m["role"], "content": redact_text(m["content"])} for m in messages]


class LLMClient:
    """Chat completion with redaction-at-send and audit metadata only (no prompt logging)."""

    def __init__(self, audit: AuditLogger | None = None) -> None:
        self.provider = os.getenv("LLM_PROVIDER", "openai").lower()
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.base_url = (
            os.getenv("LLM_BASE_URL")
            or os.getenv("LLM_API_BASE")
            or self._default_base_url()
        ).rstrip("/")
        self.audit = audit

    @staticmethod
    def _default_base_url() -> str:
        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        if provider == "anthropic":
            return "https://api.anthropic.com"
        if provider == "ollama":
            return "http://localhost:11434"
        return "https://api.openai.com/v1"

    def complete(self, messages: list[dict[str, str]], *, json_mode: bool = True) -> str:
        if not llm_enabled():
            raise RuntimeError("LLM is disabled (missing LLM_API_KEY or SPA_NO_LLM=1)")

        safe_messages = _redact_messages(messages)
        start = time.perf_counter()
        text, usage = self._dispatch(safe_messages, json_mode=json_mode)
        latency_ms = int((time.perf_counter() - start) * 1000)

        if self.audit:
            self.audit.emit(
                "llm_complete",
                task_class="llm",
                risk_class="A0",
                tools_called=[f"llm:{self.provider}"],
                outputs={
                    "model": self.model,
                    "provider": self.provider,
                    "latency_ms": latency_ms,
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "total_tokens": usage.get("total_tokens"),
                },
            )
        return text

    def _dispatch(
        self,
        messages: list[dict[str, str]],
        *,
        json_mode: bool,
    ) -> tuple[str, dict[str, int | None]]:
        if self.provider == "anthropic":
            return self._anthropic(messages)
        if self.provider == "ollama":
            return self._ollama(messages, json_mode=json_mode)
        return self._openai(messages, json_mode=json_mode)

    def _openai(
        self,
        messages: list[dict[str, str]],
        *,
        json_mode: bool,
    ) -> tuple[str, dict[str, int | None]]:
        payload: dict[str, Any] = {"model": self.model, "messages": messages}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage") or {}
        return content, {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
        }

    def _anthropic(self, messages: list[dict[str, str]]) -> tuple[str, dict[str, int | None]]:
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        chat_messages = [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "system"]
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": chat_messages,
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        url = f"{self.base_url}/v1/messages"
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        text_blocks = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
        usage = data.get("usage") or {}
        return "".join(text_blocks), {
            "prompt_tokens": usage.get("input_tokens"),
            "completion_tokens": usage.get("output_tokens"),
            "total_tokens": (usage.get("input_tokens") or 0) + (usage.get("output_tokens") or 0),
        }

    def _ollama(
        self,
        messages: list[dict[str, str]],
        *,
        json_mode: bool,
    ) -> tuple[str, dict[str, int | None]]:
        payload: dict[str, Any] = {"model": self.model, "messages": messages, "stream": False}
        if json_mode:
            payload["format"] = "json"
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
        message = data.get("message") or {}
        usage = data.get("prompt_eval_count") is not None and {
            "prompt_tokens": data.get("prompt_eval_count"),
            "completion_tokens": data.get("eval_count"),
            "total_tokens": (data.get("prompt_eval_count") or 0) + (data.get("eval_count") or 0),
        } or {}
        return message.get("content", ""), usage
