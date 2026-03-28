"""OpenAI client wrapper for Marshmello AI features."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from dotenv import dotenv_values
from openai import OpenAI

from .prompts import (
    COMMAND_SYSTEM_PROMPT,
    HYBRID_SEARCH_SYSTEM_PROMPT,
    MUSIC_CHAT_SYSTEM_PROMPT,
    SMART_PLAYLIST_SYSTEM_PROMPT,
)
from .utils import (
    normalize_command_payload,
    normalize_hybrid_search_payload,
    normalize_music_chat,
    normalize_playlist_payload,
    parse_json_object,
)


MODEL_NAME = "gpt-5.4-mini-2026-03-17"
DEFAULT_MAX_COMPLETION_TOKENS = 320


class AIClientError(RuntimeError):
    """Raised when AI client cannot complete a request."""


def _resolve_openai_api_key() -> str:
    env_names = [
        "OPENAI_API_KEY",
        "OPENAI_APIKEY",
        "OPENAI_KEY",
        "openai_api_key",
        "openai_apikey",
        "openai_key",
    ]

    for name in env_names:
        value = (os.getenv(name) or "").strip()
        if value:
            return value

    # Last-resort local fallback for environments where OS env vars are not wired correctly.
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.exists():
        values = dotenv_values(str(env_path))
        for name in env_names:
            value = str(values.get(name) or "").strip()
            if value:
                return value

    return ""


class MarshmelloAIClient:
    def __init__(self) -> None:
        api_key = _resolve_openai_api_key().strip()
        if api_key.lower().startswith("bearer "):
            api_key = api_key[7:].strip()
        if not api_key:
            raise AIClientError(
                "OPENAI_API_KEY is missing. Set OPENAI_API_KEY (or OPENAI_APIKEY/OPENAI_KEY) "
                "in the running deployment environment and redeploy."
            )
        self._client = OpenAI(api_key=api_key)

    def _call_json(self, system_prompt: str, user_prompt: str, max_completion_tokens: int = DEFAULT_MAX_COMPLETION_TOKENS) -> Dict[str, Any]:
        response = self._client.responses.create(
            model=MODEL_NAME,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": (user_prompt or "").strip()},
            ],
            max_completion_tokens=max_completion_tokens,
        )

        output_text = getattr(response, "output_text", "") or ""
        return parse_json_object(output_text, fallback={})

    def build_music_chat_query(self, user_prompt: str) -> Dict[str, str]:
        data = self._call_json(MUSIC_CHAT_SYSTEM_PROMPT, user_prompt, max_completion_tokens=180)
        return normalize_music_chat(data, user_prompt)

    def build_smart_playlist(self, user_prompt: str) -> Dict[str, Any]:
        data = self._call_json(SMART_PLAYLIST_SYSTEM_PROMPT, user_prompt, max_completion_tokens=420)
        return normalize_playlist_payload(data, user_prompt)

    def parse_player_command(self, user_prompt: str) -> Dict[str, Any]:
        data = self._call_json(COMMAND_SYSTEM_PROMPT, user_prompt, max_completion_tokens=140)
        return normalize_command_payload(data)

    def build_hybrid_search_plan(self, user_prompt: str) -> Dict[str, str]:
        data = self._call_json(HYBRID_SEARCH_SYSTEM_PROMPT, user_prompt, max_completion_tokens=240)
        return normalize_hybrid_search_payload(data, user_prompt)
