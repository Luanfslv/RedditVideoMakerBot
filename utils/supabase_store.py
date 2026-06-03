"""Persistência da GUI via Supabase PostgREST (fallback: arquivos locais)."""

from __future__ import annotations

import json
import os
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx

_CONFIG_CACHE: dict[str, object] = {"text": None, "ts": 0.0}
_BACKGROUNDS_CACHE: dict[str, object] = {"data": None, "ts": 0.0}
_CACHE_TTL_SEC = 30


def _env(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def get_url() -> str:
    return _env("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")


def get_key() -> str:
    return _env(
        "SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_KEY",
        "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
    )


def is_enabled() -> bool:
    return bool(get_url() and get_key())


@lru_cache(maxsize=1)
def _headers() -> dict[str, str]:
    key = get_key()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _rest_url(table: str) -> str:
    return f"{get_url().rstrip('/')}/rest/v1/{table}"


@lru_cache(maxsize=1)
def _client() -> httpx.Client:
    return httpx.Client(timeout=15.0)


def _request(method: str, table: str, *, headers: dict[str, str] | None = None, **kwargs: Any) -> httpx.Response:
    merged = _headers()
    if headers:
        merged.update(headers)
    response = _client().request(method, _rest_url(table), headers=merged, **kwargs)
    response.raise_for_status()
    return response


def read_config_toml(default: str) -> str:
    if not is_enabled():
        path = Path("config.toml")
        if path.exists():
            return path.read_text(encoding="utf-8")
        return default

    cached = _CONFIG_CACHE["text"]
    if cached and time.time() - float(_CONFIG_CACHE["ts"]) < _CACHE_TTL_SEC:
        return str(cached)

    response = _request(
        "GET",
        "studio_config",
        params={"select": "config_toml", "id": "eq.default", "limit": 1},
    )
    rows = response.json()
    if rows:
        text = rows[0]["config_toml"]
        _CONFIG_CACHE["text"] = text
        _CONFIG_CACHE["ts"] = time.time()
        return text

    _request(
        "POST",
        "studio_config",
        json={"id": "default", "config_toml": default},
    )
    _CONFIG_CACHE["text"] = default
    _CONFIG_CACHE["ts"] = time.time()
    return default


def write_config_toml(content: str) -> None:
    if not is_enabled():
        Path("config.toml").write_text(content, encoding="utf-8")
        return

    _CONFIG_CACHE["text"] = content
    _CONFIG_CACHE["ts"] = time.time()

    headers = _headers()
    headers["Prefer"] = "resolution=merge-duplicates,return=representation"
    _request(
        "POST",
        "studio_config",
        params={"on_conflict": "id"},
        headers=headers,
        json={"id": "default", "config_toml": content},
    )


def read_backgrounds(default: dict | None = None) -> dict:
    default = default or {}
    if not is_enabled():
        path = Path("utils/backgrounds.json")
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return default

    cached = _BACKGROUNDS_CACHE["data"]
    if cached is not None and time.time() - float(_BACKGROUNDS_CACHE["ts"]) < _CACHE_TTL_SEC:
        return dict(cached)  # type: ignore[arg-type]

    response = _request("GET", "studio_backgrounds", params={"select": "*"})
    rows = response.json()
    if not rows:
        if default:
            write_backgrounds(default)
        _BACKGROUNDS_CACHE["data"] = default
        _BACKGROUNDS_CACHE["ts"] = time.time()
        return default

    data: dict[str, list] = {}
    for row in rows:
        data[row["key"]] = [
            row["youtube_uri"],
            row["filename"],
            row["citation"],
            row["position"],
        ]
    _BACKGROUNDS_CACHE["data"] = data
    _BACKGROUNDS_CACHE["ts"] = time.time()
    return data


def write_backgrounds(data: dict) -> None:
    if not is_enabled():
        path = Path("utils/backgrounds.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8")
        return

    _BACKGROUNDS_CACHE["data"] = data
    _BACKGROUNDS_CACHE["ts"] = time.time()

    payload = []
    for key, value in data.items():
        if key == "__comment":
            continue
        payload.append(
            {
                "key": key,
                "youtube_uri": value[0],
                "filename": value[1],
                "citation": value[2],
                "position": str(value[3]),
            }
        )

    _request("DELETE", "studio_backgrounds", params={"key": "not.is.null"})
    if payload:
        _request("POST", "studio_backgrounds", json=payload)


def read_videos(default: list | None = None) -> list:
    default = default or []
    if not is_enabled():
        path = Path("video_creation/data/videos.json")
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return default

    response = _request(
        "GET",
        "studio_videos",
        params={"select": "filename,title,metadata,created_at", "order": "created_at.desc"},
    )
    rows = response.json()
    if not rows:
        return default

    return [
        {
            "filename": row["filename"],
            "title": row.get("title"),
            **row.get("metadata", {}),
            "created_at": row.get("created_at"),
        }
        for row in rows
    ]


def write_videos(data: list) -> None:
    if not is_enabled():
        path = Path("video_creation/data/videos.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8")
        return

    _request(
        "DELETE",
        "studio_videos",
        params={"id": "not.is.null"},
    )
    payload = []
    for item in data:
        metadata = {k: v for k, v in item.items() if k not in {"filename", "title", "created_at"}}
        payload.append(
            {
                "filename": item.get("filename", ""),
                "title": item.get("title"),
                "metadata": metadata,
            }
        )
    if payload:
        _request("POST", "studio_videos", json=payload)
