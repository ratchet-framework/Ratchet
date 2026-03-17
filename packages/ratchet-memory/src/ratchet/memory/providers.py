"""Pluggable LLM provider interface for memory operations."""

import json
import logging
import os
from abc import ABC, abstractmethod
from urllib import request as urlreq

logger = logging.getLogger("ratchet.memory.providers")


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system_prompt: str, user_message: str) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str | None = None, model: str = "claude-haiku-4-5", max_tokens: int = 4096) -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = model
        self.max_tokens = max_tokens
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not set — LLM calls will fail")

    def complete(self, system_prompt: str, user_message: str) -> str:
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        payload = {
            "model": self.model, "max_tokens": self.max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        }
        data = json.dumps(payload).encode("utf-8")
        req = urlreq.Request(
            "https://api.anthropic.com/v1/messages", data=data,
            headers={"Content-Type": "application/json", "x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
            method="POST",
        )
        try:
            with urlreq.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["content"][0]["text"]
        except Exception as e:
            raise RuntimeError(f"Anthropic API call failed: {e}")


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini", max_tokens: int = 4096) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model
        self.max_tokens = max_tokens

    def complete(self, system_prompt: str, user_message: str) -> str:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        payload = {
            "model": self.model, "max_tokens": self.max_tokens,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
        }
        data = json.dumps(payload).encode("utf-8")
        req = urlreq.Request(
            "https://api.openai.com/v1/chat/completions", data=data,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
            method="POST",
        )
        try:
            with urlreq.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"OpenAI API call failed: {e}")


def get_provider(name: str = "anthropic", **kwargs) -> LLMProvider:
    providers = {"anthropic": AnthropicProvider, "openai": OpenAIProvider}
    if name not in providers:
        raise ValueError(f"Unknown provider: {name!r}. Available: {list(providers.keys())}")
    return providers[name](**kwargs)
