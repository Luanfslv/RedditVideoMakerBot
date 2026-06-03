"""Normaliza payloads externos (Devvit) para o formato reddit_object do bot."""

from __future__ import annotations

import re
from typing import Any


def _clean_id(raw: str) -> str:
    return re.sub(r"[^\w\s-]", "", str(raw or "")).strip()


def normalize_reddit_object(data: dict[str, Any]) -> dict[str, Any]:
    """Valida e padroniza o JSON recebido do Studio / Devvit."""
    if "reddit_object" in data and isinstance(data["reddit_object"], dict):
        data = data["reddit_object"]

    thread_id = _clean_id(data.get("thread_id") or data.get("post_id") or "")
    if not thread_id:
        raise ValueError("thread_id é obrigatório")

    title = str(data.get("thread_title") or data.get("title") or "").strip()
    if not title:
        raise ValueError("thread_title é obrigatório")

    thread_url = str(
        data.get("thread_url")
        or data.get("url")
        or f"https://www.reddit.com/comments/{thread_id}/"
    ).strip()

    comments_in = data.get("comments") or []
    if not isinstance(comments_in, list):
        raise ValueError("comments deve ser uma lista")

    comments: list[dict[str, str]] = []
    for item in comments_in:
        if not isinstance(item, dict):
            continue
        body = str(item.get("comment_body") or item.get("body") or "").strip()
        if not body or body in ("[removed]", "[deleted]"):
            continue
        cid = _clean_id(item.get("comment_id") or item.get("id") or "")
        if not cid:
            continue
        curl = str(item.get("comment_url") or item.get("permalink") or "").strip()
        if curl and not curl.startswith("http"):
            curl = f"https://www.reddit.com{curl}" if curl.startswith("/") else curl
        comments.append(
            {
                "comment_body": body,
                "comment_url": curl,
                "comment_id": cid,
            }
        )

    storymode = bool(data.get("storymode") or data.get("thread_post"))
    obj: dict[str, Any] = {
        "thread_id": thread_id,
        "thread_title": title,
        "thread_url": thread_url,
        "is_nsfw": bool(data.get("is_nsfw")),
        "comments": comments,
    }
    if storymode and data.get("thread_post"):
        obj["thread_post"] = str(data["thread_post"]).strip()

    if not storymode and not comments:
        raise ValueError("A thread precisa de comentários ou thread_post (storymode)")

    return obj
