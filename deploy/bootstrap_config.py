#!/usr/bin/env python3
"""Gera config.toml a partir dos defaults do template (deploy em container)."""

from pathlib import Path

import toml


def strip_defaults(obj):
    if not isinstance(obj, dict):
        return obj

    meta_keys = {
        "optional",
        "type",
        "explanation",
        "example",
        "regex",
        "options",
        "default",
        "nmin",
        "nmax",
        "oob_error",
        "input_error",
        "option",
        "explantation",
    }
    if "default" in obj and any(k in obj for k in meta_keys - {"default"}):
        return obj["default"]

    return {key: strip_defaults(value) for key, value in obj.items()}


def main() -> None:
    template_path = Path("utils/.config.template.toml")
    output_path = Path("config.toml")

    if output_path.exists():
        return

    template = toml.load(template_path)
    config = strip_defaults(template)
    output_path.write_text(toml.dumps(config), encoding="utf-8")


if __name__ == "__main__":
    main()
