#!/usr/bin/env python
import argparse
import json
import math
import re
import sys
import uuid
from os import name
from pathlib import Path
from subprocess import Popen
from typing import Dict, NoReturn

from prawcore import ResponseException

from reddit.subreddit import get_subreddit_threads
from utils.render_queue import claim_next, mark_done, mark_failed
from utils import settings
from utils.cleanup import cleanup
from utils.console import print_markdown, print_step, print_substep
from utils.ffmpeg_install import ffmpeg_install
from utils.id import extract_id
from utils.version import checkversion
from video_creation.background import (
    chop_background,
    download_background_audio,
    download_background_video,
    get_background_config,
)
from video_creation.final_video import make_final_video
from video_creation.screenshot_downloader import get_screenshots_of_reddit_posts
from video_creation.voices import save_text_to_mp3

__VERSION__ = "3.4.0"

print(
    """
██████╗ ███████╗██████╗ ██████╗ ██╗████████╗    ██╗   ██╗██╗██████╗ ███████╗ ██████╗     ███╗   ███╗ █████╗ ██╗  ██╗███████╗██████╗
██╔══██╗██╔════╝██╔══██╗██╔══██╗██║╚══██╔══╝    ██║   ██║██║██╔══██╗██╔════╝██╔═══██╗    ████╗ ████║██╔══██╗██║ ██╔╝██╔════╝██╔══██╗
██████╔╝█████╗  ██║  ██║██║  ██║██║   ██║       ██║   ██║██║██║  ██║█████╗  ██║   ██║    ██╔████╔██║███████║█████╔╝ █████╗  ██████╔╝
██╔══██╗██╔══╝  ██║  ██║██║  ██║██║   ██║       ╚██╗ ██╔╝██║██║  ██║██╔══╝  ██║   ██║    ██║╚██╔╝██║██╔══██║██╔═██╗ ██╔══╝  ██╔══██╗
██║  ██║███████╗██████╔╝██████╔╝██║   ██║        ╚████╔╝ ██║██████╔╝███████╗╚██████╔╝    ██║ ╚═╝ ██║██║  ██║██║  ██╗███████╗██║  ██║
╚═╝  ╚═╝╚══════╝╚═════╝ ╚═════╝ ╚═╝   ╚═╝         ╚═══╝  ╚═╝╚═════╝ ╚══════╝ ╚═════╝     ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
"""
)
print_markdown(
    "### Thanks for using this tool! Feel free to contribute to this project on GitHub! If you have any questions, feel free to join my Discord server or submit a GitHub issue. You can find solutions to many common problems in the documentation: https://reddit-video-maker-bot.netlify.app/"
)
checkversion(__VERSION__)

reddit_id: str
reddit_object: Dict[str, str | list]


def _coerce_thread_post(reddit_object_in: Dict) -> Dict:
    """storymodemethod==1 espera thread_post como LISTA de sentenças (imagemaker + TTS
    iteram sobre ela). Fontes externas (fila/Devvit/--from-text) entregam string crua.
    Converte uma vez, no ponto central, sem mexer no contrato de PRAW (já lista)."""
    s = settings.config["settings"]
    if s["storymode"] and s["storymodemethod"] == 1:
        post = reddit_object_in.get("thread_post")
        if isinstance(post, str) and post.strip():
            from utils.posttextparser import posttextparser

            reddit_object_in["thread_post"] = posttextparser(post)
    return reddit_object_in


def run_pipeline(reddit_object_in: Dict) -> None:
    """Renderiza um vídeo a partir de um reddit_object já montado (PRAW ou Devvit)."""
    global reddit_id, reddit_object
    reddit_object = _coerce_thread_post(reddit_object_in)
    reddit_id = extract_id(reddit_object)
    print_substep(f"Thread ID is {reddit_id}", style="bold blue")
    length, number_of_comments = save_text_to_mp3(reddit_object)
    length = math.ceil(length)
    get_screenshots_of_reddit_posts(reddit_object, number_of_comments)
    bg_config = {
        "video": get_background_config("video"),
        "audio": get_background_config("audio"),
    }
    download_background_video(bg_config["video"])
    download_background_audio(bg_config["audio"])
    chop_background(bg_config, length, reddit_object)
    make_final_video(number_of_comments, length, reddit_object, bg_config)


def main(POST_ID=None) -> None:
    global reddit_id, reddit_object
    reddit_object = get_subreddit_threads(POST_ID)
    run_pipeline(reddit_object)


def main_from_queue() -> bool:
    """Processa o próximo item pendente na fila (enviado pelo Devvit / Studio)."""
    job = claim_next()
    if not job:
        print_substep("Nenhum item pendente na fila de render.", style="bold red")
        return False

    job_id = job["id"]
    title = job.get("title") or job.get("thread_id")
    print_step(f"Fila: renderizando «{title}» (job {job_id})")
    try:
        run_pipeline(job["reddit_object"])
        mark_done(job_id)
        print_substep("Fila: item concluído.", style="bold green")
        return True
    except Exception as err:
        mark_failed(job_id, str(err))
        raise


def main_from_text(path: str) -> None:
    """Renderiza um vídeo story-mode a partir de um JSON local, SEM Reddit API,
    SEM navegador headless e SEM login. Formato do arquivo:

        {"title": "...", "text": "história aqui...", "id": "opcional"}

    Use com storymode=true + storymodemethod=1 no config.toml. Render 100% local
    (PIL + ffmpeg + TTS), hospedável em qualquer container sem Chromium nem credenciais
    do Reddit."""
    file_path = Path(path)
    if not file_path.exists():
        print_substep(f"Arquivo não encontrado: {path}", style="bold red")
        sys.exit(1)

    data = json.loads(file_path.read_text(encoding="utf-8"))
    title = str(data.get("title") or data.get("thread_title") or "").strip()
    text = str(data.get("text") or data.get("thread_post") or "").strip()
    if not title or not text:
        print_substep("JSON precisa de 'title' e 'text' não-vazios.", style="bold red")
        sys.exit(1)

    if not settings.config["settings"]["storymode"]:
        print_substep(
            "Aviso: storymode=false no config.toml. --from-text só renderiza a história; "
            "ative storymode=true (e storymodemethod=1) para hosting sem navegador.",
            style="bold yellow",
        )

    thread_id = re.sub(r"[^\w-]", "", str(data.get("id") or data.get("thread_id") or "")).strip()
    if not thread_id:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]
        thread_id = slug or uuid.uuid4().hex[:10]

    reddit_object = {
        "thread_id": thread_id,
        "thread_title": title,
        "thread_url": str(data.get("url") or "").strip(),
        "is_nsfw": bool(data.get("is_nsfw", False)),
        "comments": [],
        "thread_post": text,  # vira lista em run_pipeline quando storymodemethod==1
    }
    print_step(f"Texto local: renderizando «{title}» (id {thread_id})")
    run_pipeline(reddit_object)


def run_many(times) -> None:
    for x in range(1, times + 1):
        print_step(
            f'on the {x}{("th", "st", "nd", "rd", "th", "th", "th", "th", "th", "th")[x % 10]} iteration of {times}'
        )
        main()
        Popen("cls" if name == "nt" else "clear", shell=True).wait()


def shutdown() -> NoReturn:
    if "reddit_id" in globals():
        print_markdown("## Clearing temp files")
        cleanup(reddit_id)

    print("Exiting...")
    sys.exit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RedditVideoMakerBot")
    parser.add_argument(
        "--from-queue",
        action="store_true",
        help="Renderiza o próximo vídeo da fila (enviado pelo Devvit / Studio)",
    )
    parser.add_argument(
        "--from-text",
        dest="from_text",
        metavar="FILE",
        help="Renderiza story-mode a partir de um JSON local {title,text} — sem Reddit API, sem navegador, sem login",
    )
    cli_args, _unknown = parser.parse_known_args()

    if sys.version_info.major != 3 or sys.version_info.minor not in [10, 11, 12]:
        print(
            "Hey! Congratulations, you've made it so far (which is pretty rare with no Python 3.10). Unfortunately, this program only works on Python 3.10. Please install Python 3.10 and try again."
        )
        sys.exit()
    ffmpeg_install()
    directory = Path().absolute()
    config = settings.check_toml(
        f"{directory}/utils/.config.template.toml", f"{directory}/config.toml"
    )
    config is False and sys.exit()

    if (
        not settings.config["settings"]["tts"]["tiktok_sessionid"]
        or settings.config["settings"]["tts"]["tiktok_sessionid"] == ""
    ) and config["settings"]["tts"]["voice_choice"] == "tiktok":
        print_substep(
            "TikTok voice requires a sessionid! Check our documentation on how to obtain one.",
            "bold red",
        )
        sys.exit()
    try:
        if cli_args.from_text:
            main_from_text(cli_args.from_text)
        elif cli_args.from_queue:
            if not main_from_queue():
                sys.exit(0)
        elif config["reddit"]["thread"]["post_id"]:
            for index, post_id in enumerate(config["reddit"]["thread"]["post_id"].split("+")):
                index += 1
                print_step(
                    f'on the {index}{("st" if index % 10 == 1 else ("nd" if index % 10 == 2 else ("rd" if index % 10 == 3 else "th")))} post of {len(config["reddit"]["thread"]["post_id"].split("+"))}'
                )
                main(post_id)
                Popen("cls" if name == "nt" else "clear", shell=True).wait()
        elif config["settings"]["times_to_run"]:
            run_many(config["settings"]["times_to_run"])
        else:
            main()
    except KeyboardInterrupt:
        shutdown()
    except ResponseException:
        print_markdown("## Invalid credentials")
        print_markdown("Please check your credentials in the config.toml file")
        shutdown()
    except Exception as err:
        config["settings"]["tts"]["tiktok_sessionid"] = "REDACTED"
        config["settings"]["tts"]["elevenlabs_api_key"] = "REDACTED"
        config["settings"]["tts"]["openai_api_key"] = "REDACTED"
        print_step(
            f"Sorry, something went wrong with this version! Try again, and feel free to report this issue at GitHub or the Discord community.\n"
            f"Version: {__VERSION__} \n"
            f"Error: {err} \n"
            f'Config: {config["settings"]}'
        )
        raise err
