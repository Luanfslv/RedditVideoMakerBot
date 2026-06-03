"""Rotas Flask: ingestão Devvit → fila de render do Studio."""

from __future__ import annotations

import os

from flask import jsonify, request

from utils import render_queue
from utils.thread_payload import normalize_reddit_object


def ingest_secret() -> str:
    return os.getenv("STUDIO_INGEST_SECRET", "").strip()


def authorize_ingest() -> bool:
    secret = ingest_secret()
    if not secret:
        return False
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:].strip()
    else:
        token = request.headers.get("X-Studio-Ingest-Secret", "").strip()
    return token == secret


def register_routes(app):
    @app.route("/api/devvit/ingest", methods=["POST"])
    def devvit_ingest():
        if not authorize_ingest():
            return jsonify({"ok": False, "error": "Não autorizado"}), 401

        data = request.get_json(silent=True)
        if not data:
            return jsonify({"ok": False, "error": "JSON inválido"}), 400

        try:
            obj = normalize_reddit_object(data)
            job = render_queue.enqueue(obj, source=str(data.get("source") or "devvit"))
            return jsonify(
                {
                    "ok": True,
                    "job_id": job["id"],
                    "thread_id": job["thread_id"],
                    "title": job["title"],
                    "message": "Thread enfileirada. Rode python main.py --from-queue na sua máquina.",
                }
            ), 201
        except ValueError as err:
            return jsonify({"ok": False, "error": str(err)}), 400

    @app.route("/api/render-queue", methods=["GET"])
    def render_queue_list():
        jobs = render_queue.list_jobs(limit=30)
        return jsonify({"ok": True, "jobs": jobs})

    @app.route("/api/devvit/health", methods=["GET"])
    def devvit_health():
        return jsonify(
            {
                "ok": True,
                "ingest_configured": bool(ingest_secret()),
            }
        )
