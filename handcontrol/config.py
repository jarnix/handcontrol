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
    vertical_max_deg: float = 35.0      # a hand within this angle of straight up/down is "pointing"
    min_direction_len: float = 0.6      # wrist->knuckle length in hand widths; shorter = foreshortened, ignored


@dataclass(frozen=True)
class StartMenuSettings:
    """Bomb: a fist held briefly, then opened into a flat hand."""

    fist_frames: int = 6            # frames the fist must be held before the opening counts
    open_within_frames: int = 12    # frames allowed between leaving the fist and reaching the open hand
    cooldown_s: float = 1.5


@dataclass(frozen=True)
class YoutubeSettings:
    """Rock-on held."""

    hold_frames: int = 18
    cooldown_s: float = 2.0
    url: str = "https://www.youtube.com"


@dataclass(frozen=True)
class ShowDesktopSettings:
    """Middle finger held."""

    hold_frames: int = 18
    cooldown_s: float = 1.5


@dataclass(frozen=True)
class VolumeSettings:
    """Open hand pointing up or down, repeating while held."""

    engage_frames: int = 10
    repeat_frames: int = 5


@dataclass(frozen=True)
class ScrollSettings:
    engage_frames: int = 3
    release_frames: int = 5
    deadzone_widths: float = 0.02
    gain_notches_per_width: float = 3.0
    smoothing: float = 0.5
    wheel_step: int = 120


@dataclass(frozen=True)
class Settings:
    camera: CameraSettings = field(default_factory=CameraSettings)
    tracker: TrackerSettings = field(default_factory=TrackerSettings)
    hand: HandSettings = field(default_factory=HandSettings)
    start_menu: StartMenuSettings = field(default_factory=StartMenuSettings)
    youtube: YoutubeSettings = field(default_factory=YoutubeSettings)
    show_desktop: ShowDesktopSettings = field(default_factory=ShowDesktopSettings)
    volume: VolumeSettings = field(default_factory=VolumeSettings)
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
