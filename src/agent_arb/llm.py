"""The only code that talks to a model.

One OpenAI-compatible HTTP client covers Ollama, vLLM, LM Studio and
llama.cpp. ``FakeModel`` stands in for tests and evals so nothing leaves
the process. Both expose ``complete_json``: a system prompt, a user prompt,
and back comes a parsed JSON object.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any, Protocol

import httpx


class ModelError(RuntimeError):
    pass


class Model(Protocol):
    name: str

    def complete_json(self, system: str, user: str) -> dict[str, Any]: ...


def _extract_json(text: str) -> dict[str, Any]:
    """Pull the first JSON object out of a reply, tolerating code fences."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ModelError("model reply contained no JSON object")
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        raise ModelError(f"model reply was not valid JSON: {e}") from e
    if not isinstance(parsed, dict):
        raise ModelError("model reply was JSON but not an object")
    return parsed


class OpenAICompatibleModel:
    """Chat completions against any OpenAI-compatible endpoint, temperature zero."""

    def __init__(self, base_url: str, model: str, api_key: str = "", timeout: float = 180.0):
        self.base_url = base_url.rstrip("/")
        self.name = model
        self._client = httpx.Client(
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
        )

    def complete_json(self, system: str, user: str) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.name,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }
        last: Exception | None = None
        for attempt in range(2):
            if attempt == 1:
                body.pop("response_format", None)
            try:
                resp = self._client.post(f"{self.base_url}/chat/completions", json=body)
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                return _extract_json(content)
            except (httpx.HTTPError, KeyError, ModelError) as e:
                last = e
        raise ModelError(f"model call failed: {last}")

    def ping(self) -> list[str]:
        resp = self._client.get(f"{self.base_url}/models")
        resp.raise_for_status()
        return [m["id"] for m in resp.json().get("data", [])]


class FakeModel:
    """Deterministic stand-in. ``responder`` maps (system, user) to a dict."""

    def __init__(self, responder: Callable[[str, str], dict[str, Any]], name: str = "fake"):
        self.name = name
        self._responder = responder
        self.calls: list[tuple[str, str]] = []

    def complete_json(self, system: str, user: str) -> dict[str, Any]:
        self.calls.append((system, user))
        return self._responder(system, user)
