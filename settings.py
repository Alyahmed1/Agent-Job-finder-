"""Tiny local settings file: remembers which theme you picked."""
import json
from pathlib import Path

PATH = Path(__file__).parent / "settings.json"


def load_theme(valid, default):
    try:
        name = json.loads(PATH.read_text(encoding="utf-8")).get("theme", default)
    except (OSError, ValueError):
        return default
    return name if name in valid else default


def save_theme(name):
    PATH.write_text(json.dumps({"theme": name}), encoding="utf-8")
