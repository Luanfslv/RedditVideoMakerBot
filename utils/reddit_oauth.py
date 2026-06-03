"""OAuth Reddit (web app) → salva refresh_token no config do Studio."""

from __future__ import annotations

import base64
import os
import secrets
from pathlib import Path
from urllib.parse import urlencode

import httpx
import tomlkit
from flask import flash, redirect, request, session, url_for

from utils import supabase_store

REDDIT_AUTHORIZE_URL = "https://www.reddit.com/api/v1/authorize"
REDDIT_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
REDDIT_ME_URL = "https://oauth.reddit.com/api/v1/me"
DEFAULT_REDIRECT_URI = "https://videomaker.aceleravaquinha.com.br/auth/reddit/callback"
OAUTH_SCOPES = ["identity", "read", "history"]
USER_AGENT = "RedditMakerStudio/1.0 by u/RedditVideoMakerBot"


def redirect_uri() -> str:
    return os.getenv("REDDIT_OAUTH_REDIRECT_URI", DEFAULT_REDIRECT_URI).strip()


def _default_config_toml() -> str:
    path = Path("config.toml")
    if path.exists():
        return path.read_text(encoding="utf-8")
    import toml
    from deploy.bootstrap_config import strip_defaults

    return toml.dumps(strip_defaults(toml.load("utils/.config.template.toml")))


def load_config_document():
    return tomlkit.loads(supabase_store.read_config_toml(_default_config_toml()))


def save_config_document(doc) -> None:
    supabase_store.write_config_toml(tomlkit.dumps(doc))


def get_reddit_creds() -> dict:
    doc = load_config_document()
    creds = doc.get("reddit", {}).get("creds", {})
    return {
        "client_id": str(creds.get("client_id", "") or "").strip(),
        "client_secret": str(creds.get("client_secret", "") or "").strip(),
        "username": str(creds.get("username", "") or "").strip(),
        "refresh_token": str(creds.get("refresh_token", "") or "").strip(),
    }


def _missing_creds_message() -> str:
    return (
        "Preencha Client ID e Client Secret em Configurações e salve antes de conectar. "
        "O app no Reddit deve ser tipo web app com redirect "
        f"{redirect_uri()}"
    )


def build_authorize_url(state: str) -> str:
    creds = get_reddit_creds()
    if not creds["client_id"] or not creds["client_secret"]:
        raise ValueError(_missing_creds_message())

    params = {
        "client_id": creds["client_id"],
        "response_type": "code",
        "state": state,
        "redirect_uri": redirect_uri(),
        "duration": "permanent",
        "scope": " ".join(OAUTH_SCOPES),
    }
    return f"{REDDIT_AUTHORIZE_URL}?{urlencode(params)}"


def exchange_code(code: str) -> dict:
    creds = get_reddit_creds()
    if not creds["client_id"] or not creds["client_secret"]:
        raise ValueError(_missing_creds_message())

    basic = base64.b64encode(
        f"{creds['client_id']}:{creds['client_secret']}".encode()
    ).decode()

    with httpx.Client(timeout=30.0) as client:
        token_res = client.post(
            REDDIT_TOKEN_URL,
            headers={
                "Authorization": f"Basic {basic}",
                "User-Agent": USER_AGENT,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri(),
            },
        )
        token_res.raise_for_status()
        token_data = token_res.json()

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            raise ValueError("Reddit não retornou refresh_token. Tente autorizar de novo.")

        me_res = client.get(
            REDDIT_ME_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "User-Agent": USER_AGENT,
            },
        )
        me_res.raise_for_status()
        me = me_res.json()

    username = str(me.get("name") or "").strip()
    if not username:
        raise ValueError("Não foi possível obter o usuário Reddit.")

    return {
        "refresh_token": refresh_token,
        "username": username,
    }


def persist_oauth_tokens(refresh_token: str, username: str) -> None:
    doc = load_config_document()
    if "reddit" not in doc:
        doc["reddit"] = tomlkit.table()
    if "creds" not in doc["reddit"]:
        doc["reddit"]["creds"] = tomlkit.table()

    doc["reddit"]["creds"]["refresh_token"] = refresh_token
    doc["reddit"]["creds"]["username"] = username
    doc["reddit"]["creds"]["2fa"] = False
    save_config_document(doc)


def register_routes(app):
    @app.route("/auth/reddit")
    def auth_reddit_start():
        try:
            state = secrets.token_urlsafe(32)
            session["reddit_oauth_state"] = state
            return redirect(build_authorize_url(state))
        except ValueError as err:
            flash(str(err), "error")
            return redirect(url_for("settings"))

    @app.route("/auth/reddit/callback")
    def auth_reddit_callback():
        error = request.args.get("error")
        if error:
            flash(f"Reddit recusou a autorização: {error}", "error")
            return redirect(url_for("settings"))

        state = request.args.get("state", "")
        code = request.args.get("code", "")
        expected = session.pop("reddit_oauth_state", None)

        if not code:
            flash("Código OAuth ausente. Tente conectar de novo.", "error")
            return redirect(url_for("settings"))

        if not expected or state != expected:
            flash("Sessão OAuth inválida (state). Tente conectar de novo.", "error")
            return redirect(url_for("settings"))

        try:
            tokens = exchange_code(code)
            persist_oauth_tokens(tokens["refresh_token"], tokens["username"])
            flash(f"Conta u/{tokens['username']} conectada via Reddit OAuth!", "success")
        except httpx.HTTPStatusError as err:
            detail = err.response.text[:200] if err.response else str(err)
            flash(f"Erro ao trocar código OAuth: {detail}", "error")
        except Exception as err:
            flash(str(err), "error")

        return redirect(url_for("settings"))
