"""Centralised config loader — reads ``configs/settings.yaml``."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parent.parent  # project root


@lru_cache(maxsize=1)
def get_settings() -> dict:
    """Load and cache the YAML settings file."""
    settings_path = _ROOT / "configs" / "settings.yaml"
    if not settings_path.exists():
        raise FileNotFoundError(f"Settings file not found: {settings_path}")
    with open(settings_path, "r") as f:
        return yaml.safe_load(f)
