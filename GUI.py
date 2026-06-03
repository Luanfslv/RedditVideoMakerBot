import os
import webbrowser
from pathlib import Path

# Used "tomlkit" instead of "toml" because it doesn't change formatting on "dump"
import tomlkit
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

import utils.gui_utils as gui
from utils import supabase_store

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "4000"))

# Configure application
app = Flask(
    __name__,
    template_folder="GUI",
    static_folder="GUI/static",
    static_url_path="/static",
)

# Configure secret key only to use 'flash'
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

DOCS_GUIDE_URL = "/docs#gerar-video"
DOCS_REDDIT_URL = "/docs#credenciais-reddit"


@app.context_processor
def inject_docs():
    return {
        "docs_guide_url": DOCS_GUIDE_URL,
        "docs_reddit_url": DOCS_REDDIT_URL,
    }


def _default_config_toml() -> str:
    path = Path("config.toml")
    if path.exists():
        return path.read_text(encoding="utf-8")

    import toml

    from deploy.bootstrap_config import strip_defaults

    return toml.dumps(strip_defaults(toml.load("utils/.config.template.toml")))
# Cache static assets; HTML stays fresh for config/UI changes
@app.after_request
def after_request(response):
    if request.path.startswith("/static/"):
        response.headers["Cache-Control"] = "public, max-age=604800, immutable"
    else:
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
    return response


# Display index.html
@app.route("/")
def index():
    return render_template(
        "index.html",
        file="videos.json",
        active="dashboard",
        page_title="Dashboard",
        page_sub="Visão geral da sua produção de vídeos",
    )


@app.route("/backgrounds", methods=["GET"])
def backgrounds():
    return render_template(
        "backgrounds.html",
        file="backgrounds.json",
        active="backgrounds",
        page_title="Fundos",
        page_sub="Vídeos de gameplay usados como pano de fundo",
    )


# UI-only screens (the bot itself is launched from the CLI via `python main.py`)
@app.route("/create", methods=["GET"])
def create():
    return render_template(
        "create.html",
        active="create",
        page_title="Criar vídeo",
        page_sub="Monte um short a partir de uma thread do Reddit",
    )


@app.route("/queue", methods=["GET"])
def queue():
    return render_template(
        "queue.html",
        active="queue",
        page_title="Fila de render",
        page_sub="Acompanhe os vídeos sendo processados",
    )


@app.route("/docs")
def docs():
    return render_template(
        "docs.html",
        active="docs",
        page_title="Documentação",
        page_sub="Como usar o RedditMaker Studio e gerar seus vídeos",
    )


@app.route("/about")
def about():
    return render_template(
        "about.html",
        active="about",
        page_title="Sobre",
        page_sub="Conheça o RedditMaker Studio e o RedditVideoMakerBot",
    )


@app.route("/background/add", methods=["POST"])
def background_add():
    # Get form values
    youtube_uri = request.form.get("youtube_uri").strip()
    filename = request.form.get("filename").strip()
    citation = request.form.get("citation").strip()
    position = request.form.get("position").strip()

    gui.add_background(youtube_uri, filename, citation, position)

    return redirect(url_for("backgrounds"))


@app.route("/background/delete", methods=["POST"])
def background_delete():
    key = request.form.get("background-key")
    gui.delete_background(key)

    return redirect(url_for("backgrounds"))


@app.route("/settings", methods=["GET", "POST"])
def settings():
    config_load = tomlkit.loads(supabase_store.read_config_toml(_default_config_toml()))
    config = gui.get_config(config_load)

    # Get checks for all values
    checks = gui.get_checks()

    if request.method == "POST":
        # Get data from form as dict
        data = request.form.to_dict()

        # Change settings
        config = gui.modify_settings(data, config_load, checks)

    return render_template(
        "settings.html",
        file="config.toml",
        data=config,
        checks=checks,
        active="settings",
        page_title="Configurações",
        page_sub="Credenciais, vozes e preferências de geração",
    )


# Make videos.json accessible
@app.route("/videos.json")
def videos_json():
    return jsonify(supabase_store.read_videos([]))


@app.route("/backgrounds.json")
def backgrounds_json():
    return jsonify(supabase_store.read_backgrounds({}))


# Make videos in results folder accessible
@app.route("/results/<path:name>")
def results(name):
    return send_from_directory("results", name, as_attachment=True)


# Make voices samples in voices folder accessible
@app.route("/voices/<path:name>")
def voices(name):
    return send_from_directory("GUI/voices", name, as_attachment=True)


if __name__ == "__main__":
    if os.getenv("FLASK_ENV") != "production":
        webbrowser.open(f"http://{HOST}:{PORT}", new=2)
        print("Website opened in new tab. Refresh if it didn't load.")
    app.run(host=HOST, port=PORT)
