"""Settings with defaults, optionally overridden by a TOML file.

Defaults are the values from the design spec (section 6). A config file at
%LOCALAPPDATA%\\HandControl\\config.toml may override any subset of keys.
"""

from __future__ import annotations

import logging
import os
import tomllib
from dataclasses import dataclass, field, fields, replace
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CameraSettings:
    index: int = 0
    width: int = 1280
    height: int = 720


@dataclass(frozen=True)
class TrackerSettings:
    min_hand_detection_confidence: float = 0.5
    min_hand_presence_confidence: float = 0.5
    min_tracking_confidence: float = 0.5


@dataclass(frozen=True)
class HandSettings:
    finger_extended_angle_deg: float = 150.0
    fingers_joined_max_m: float = 0.03


@dataclass(frozen=True)
class StartMenuSettings:
    swipe_distance_palms: float = 1.5
    swipe_window_s: float = 0.5
    swipe_cooldown_s: float = 1.5


@dataclass(frozen=True)
class ScrollSettings:
    engage_frames: int = 3
    release_frames: int = 5
    deadzone_palms: float = 0.02
    gain_notches_per_palm: float = 4.0
    smoothing: float = 0.5
    wheel_step: int = 120


@dataclass(frozen=True)
class Settings:
    camera: CameraSettings = field(default_factory=CameraSettings)
    tracker: TrackerSettings = field(default_factory=TrackerSettings)
    hand: HandSettings = field(default_factory=HandSettings)
    start_menu: StartMenuSettings = field(default_factory=StartMenuSettings)
    scroll: ScrollSettings = field(default_factory=ScrollSettings)


def app_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "HandControl"


def default_config_path() -> Path:
    return app_data_dir() / "config.toml"


def settings_from_dict(data: dict) -> Settings:
    """Build Settings from a parsed TOML dict; unknown keys are logged and ignored."""
    section_names = {f.name for f in fields(Settings)}
    for key in data:
        if key not in section_names:
            log.warning("config: unknown section [%s] ignored", key)
    sections = {}
    for section_field in fields(Settings):
        section = data.get(section_field.name)
        if section is None:
            continue
        if not isinstance(section, dict):
            log.warning("config: section [%s] must be a table, ignoring", section_field.name)
            continue
        default = section_field.default_factory()  # type: ignore[misc]
        known = {f.name for f in fields(default)}
        overrides = {}
        for key, value in section.items():
            if key in known:
                overrides[key] = value
            else:
                log.warning("config: unknown key %s.%s ignored", section_field.name, key)
        sections[section_field.name] = replace(default, **overrides)
    return Settings(**sections)


def load_settings(path: Path | None = None) -> Settings:
    """Load settings from ``path`` (default: the per-user config file); fall back to defaults."""
    path = path or default_config_path()
    if not path.exists():
        log.info("config: no file at %s, using defaults", path)
        return Settings()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError) as exc:
        log.error("config: cannot read %s (%s), using defaults", path, exc)
        return Settings()
    return settings_from_dict(data)
