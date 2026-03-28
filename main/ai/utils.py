"""Utilities for robust JSON parsing and schema normalization."""

from __future__ import annotations

import json
from typing import Any, Dict, List


def parse_json_object(raw_text: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    text = (raw_text or "").strip()
    if not text:
        return fallback

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Best-effort recovery when model wraps JSON with extra text.
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and first < last:
        try:
            parsed = json.loads(text[first : last + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return fallback

    return fallback


def normalize_music_chat(data: Dict[str, Any], user_prompt: str) -> Dict[str, str]:
    query = str(data.get("query") or user_prompt or "trending songs").strip()
    mood = str(data.get("mood") or "mixed").strip()
    genre = str(data.get("genre") or "mixed").strip()
    return {
        "query": query,
        "mood": mood,
        "genre": genre,
    }


def normalize_playlist_payload(data: Dict[str, Any], user_prompt: str) -> Dict[str, Any]:
    title = str(data.get("title") or "AI Playlist").strip()
    description = str(data.get("description") or f"Generated for: {user_prompt}").strip()

    raw_queries = data.get("queries")
    queries: List[str] = []
    if isinstance(raw_queries, list):
        queries = [str(item).strip() for item in raw_queries if str(item).strip()]

    if not queries:
        queries = [str(user_prompt or "chill music").strip()]

    return {
        "title": title,
        "description": description,
        "queries": queries[:10],
    }


def normalize_command_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    allowed = {
        "play",
        "pause",
        "play_next",
        "play_previous",
        "repeat",
        "play_similar",
        "toggle_like",
        "unknown",
    }

    action = str(data.get("action") or "unknown").strip().lower()
    if action not in allowed:
        action = "unknown"

    confidence_raw = data.get("confidence", 0)
    try:
        confidence = float(confidence_raw)
    except (TypeError, ValueError):
        confidence = 0.0

    confidence = max(0.0, min(1.0, confidence))
    reason = str(data.get("reason") or "").strip()

    return {
        "action": action,
        "confidence": confidence,
        "reason": reason,
    }


def normalize_hybrid_search_payload(data: Dict[str, Any], user_prompt: str) -> Dict[str, str]:
    keyword_query = str(data.get("keyword_query") or user_prompt or "music").strip()
    semantic_query = str(data.get("semantic_query") or user_prompt or "music").strip()
    mood = str(data.get("mood") or "any").strip()
    genre = str(data.get("genre") or "any").strip()
    era = str(data.get("era") or "any").strip()

    return {
        "keyword_query": keyword_query,
        "semantic_query": semantic_query,
        "mood": mood,
        "genre": genre,
        "era": era,
    }
