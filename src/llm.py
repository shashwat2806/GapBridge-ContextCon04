from __future__ import annotations

import json
import time
from typing import Any

import ollama

OLLAMA_HOST = "http://127.0.0.1:11434"


class LocalModelError(RuntimeError):
    pass


def _field(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _parse_json_object(content: str) -> dict:
    decoder = json.JSONDecoder()
    stripped = content.strip()
    for offset, character in enumerate(stripped):
        if character != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(stripped[offset:])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    raise ValueError("Local model response did not contain a JSON object.")


class LocalLLM:
    """Ollama client pinned to loopback; this implementation has no cloud route."""

    def __init__(
        self,
        model: str = "qwen2.5:3b-instruct",
        embedding_model: str = "nomic-embed-text",
    ):
        self.model = model
        self.embedding_model = embedding_model
        self.client = ollama.Client(host=OLLAMA_HOST, timeout=180.0)

    def check_available(self) -> list[str]:
        try:
            response = self.client.list()
        except Exception as exc:
            raise LocalModelError(
                "Cannot reach Ollama at 127.0.0.1:11434. Start Ollama locally, then retry. "
                "No external API is used."
            ) from exc

        models = _field(response, "models", []) or []
        names = []
        for item in models:
            name = _field(item, "model") or _field(item, "name")
            if name:
                names.append(str(name))
        normalized = {name.removesuffix(":latest") for name in names}
        if self.model.removesuffix(":latest") not in normalized:
            raise LocalModelError(
                f"Local model '{self.model}' is not installed. Pull it with: ollama pull {self.model}"
            )
        return names

    def chat_json(self, system: str, user: str, retries: int = 2) -> dict:
        last_error: Exception | None = None
        for attempt in range(retries):
            try:
                response = self.client.chat(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    format="json",
                    options={"temperature": 0, "seed": 42},
                )
                message = _field(response, "message", {})
                content = _field(message, "content", "")
                return _parse_json_object(str(content))
            except ValueError as exc:
                last_error = exc
                if attempt + 1 < retries:
                    time.sleep(0.4)
            except Exception as exc:
                raise LocalModelError(f"Local chat call failed: {exc}") from exc
        raise LocalModelError(str(last_error or "Local model returned invalid JSON."))

    def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = self.client.embed(model=model or self.embedding_model, input=texts)
            vectors = _field(response, "embeddings")
            if not vectors:
                raise ValueError("Ollama returned no embedding vectors.")
            return [[float(value) for value in vector] for vector in vectors]
        except Exception as exc:
            raise LocalModelError(f"Local embedding call failed: {exc}") from exc
