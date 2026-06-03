"""Fila de render: Devvit → Studio → python main.py --from-queue."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils import supabase_store
from utils.thread_payload import normalize_reddit_object

_LOCAL_PATH = Path("video_creation/data/render_queue.json")
_STATUSES = ("pending", "processing", "done", "failed")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_local() -> list[dict[str, Any]]:
    if not _LOCAL_PATH.exists():
        return []
    return json.loads(_LOCAL_PATH.read_text(encoding="utf-8"))


def _save_local(rows: list[dict[str, Any]]) -> None:
    _LOCAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    _LOCAL_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def enqueue(reddit_object: dict[str, Any], *, source: str = "devvit") -> dict[str, Any]:
    obj = normalize_reddit_object(reddit_object)
    job = {
        "id": str(uuid.uuid4()),
        "thread_id": obj["thread_id"],
        "title": obj["thread_title"],
        "reddit_object": obj,
        "status": "pending",
        "source": source,
        "error_message": None,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }

    if supabase_store.is_enabled():
        response = supabase_store._request(
            "POST",
            "studio_render_queue",
            json={
                "thread_id": job["thread_id"],
                "title": job["title"],
                "reddit_object": obj,
                "status": "pending",
                "source": source,
            },
        )
        rows = response.json()
        if rows:
            job["id"] = rows[0]["id"]
        return job

    rows = _load_local()
    rows.insert(0, job)
    _save_local(rows)
    return job


def list_jobs(*, limit: int = 50) -> list[dict[str, Any]]:
    if supabase_store.is_enabled():
        response = supabase_store._request(
            "GET",
            "studio_render_queue",
            params={
                "select": "id,thread_id,title,status,source,error_message,created_at,updated_at",
                "order": "created_at.desc",
                "limit": limit,
            },
        )
        return response.json()

    return _load_local()[:limit]


def _patch_job(job_id: str, **fields: Any) -> None:
    fields["updated_at"] = _now_iso()
    if supabase_store.is_enabled():
        supabase_store._request(
            "PATCH",
            "studio_render_queue",
            params={"id": f"eq.{job_id}"},
            json=fields,
        )
        return

    rows = _load_local()
    for row in rows:
        if row["id"] == job_id:
            row.update(fields)
            break
    _save_local(rows)


def claim_next() -> dict[str, Any] | None:
    if supabase_store.is_enabled():
        response = supabase_store._request(
            "GET",
            "studio_render_queue",
            params={
                "select": "id,thread_id,title,reddit_object,status,source",
                "status": "eq.pending",
                "order": "created_at.asc",
                "limit": 1,
            },
        )
        rows = response.json()
        if not rows:
            return None
        job = rows[0]
        _patch_job(job["id"], status="processing")
        job["status"] = "processing"
        return job

    rows = _load_local()
    for row in rows:
        if row.get("status") == "pending":
            _patch_job(row["id"], status="processing")
            row["status"] = "processing"
            return row
    return None


def mark_done(job_id: str) -> None:
    _patch_job(job_id, status="done", error_message=None)


def mark_failed(job_id: str, message: str) -> None:
    _patch_job(job_id, status="failed", error_message=message[:500])
