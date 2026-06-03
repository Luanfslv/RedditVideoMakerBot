#!/usr/bin/env python3
"""Popula o Supabase com dados locais iniciais (config + backgrounds)."""

from pathlib import Path

from deploy.bootstrap_config import main as bootstrap_config
from utils import supabase_store


def main() -> None:
    if not supabase_store.is_enabled():
        raise SystemExit("Defina SUPABASE_URL e SUPABASE_KEY (ou NEXT_PUBLIC_*) antes de rodar.")

    bootstrap_config()
    default_config = Path("config.toml").read_text(encoding="utf-8")
    supabase_store.write_config_toml(default_config)

    backgrounds_path = Path("utils/backgrounds.json")
    if backgrounds_path.exists():
        import json

        backgrounds = json.loads(backgrounds_path.read_text(encoding="utf-8"))
        supabase_store.write_backgrounds(backgrounds)

    print("Seed concluído: studio_config + studio_backgrounds.")


if __name__ == "__main__":
    main()
