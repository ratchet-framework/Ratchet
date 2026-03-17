"""Configuration loading and validation for Ratchet agents."""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("ratchet.core.config")

REQUIRED_FIELDS = {"name", "timezone"}

DEFAULTS = {
    "units": "imperial",
    "locale": "en-US",
    "heartbeat_interval_minutes": 30,
    "quiet_hours": {"start": "23:00", "end": "07:00"},
}


def load_config(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)

    missing = REQUIRED_FIELDS - set(config.keys())
    if missing:
        raise ValueError(f"Missing required config fields: {missing}")

    for key, default in DEFAULTS.items():
        if key not in config:
            config[key] = default

    logger.info(f"Loaded config for agent '{config['name']}' (tz: {config['timezone']})")
    return config
