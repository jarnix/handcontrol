# HandControl Implementation Plan

> **Superseded in part (2026-09-22):** the Start-menu swipe gesture (Tasks 5 and 12 steps 1-3) was replaced by the v1.1 gesture set. See `2026-09-22-handcontrol-gestures-v1.1.md` and spec v1.1.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Windows tray app that watches the webcam with MediaPipe and turns two hand gestures into input: an open-palm upward swipe presses the Windows key, and a two-finger vertical drag scrolls the focused app in the natural direction.

**Architecture:** The tray (pystray) runs on the main thread. A pipeline thread loops at ~30 Hz: OpenCV frame → MediaPipe `HandLandmarker` → pure-Python `HandPose` → two gesture state machines → actions injected with `SendInput`. All decision logic (`config`, `hand`, `gestures`, action types) is pure and unit-tested with synthetic landmarks; camera, tracker, tray, preview and `winput` are thin adapters checked manually through a preview window.

**Tech Stack:** Python 3.13, uv, mediapipe 1.0.1 (Tasks API), opencv-python, pystray, Pillow, stdlib ctypes/tomllib, pytest.

**Spec:** `docs/superpowers/specs/2026-09-22-handcontrol-design.md`

## Global Constraints

- Python `>=3.13`; the project is managed with `uv` (`uv sync`, `uv run ...`). Never `pip install` into the system interpreter.
- Dependencies: `mediapipe>=1.0.1,<2`, `opencv-python`, `numpy`, `pystray`, `pillow`; dev: `pytest`. MediaPipe 1.0 has **no** `mp.solutions`; only the Tasks API (`mediapipe.tasks.python.vision`) exists.
- Flat package layout: `handcontrol/` at the repo root. `config.py`, `hand.py`, `gestures/*`, and the action *types* in `actions.py` must never import `cv2`, `mediapipe`, `pystray` or `ctypes`. Tests must run with no camera and without importing MediaPipe.
- Coordinates: image landmarks are normalized 0..1 with y growing **downward**, so "up" means decreasing y. All motion thresholds are in **palm units** (distance divided by `palm_size`, the image-space wrist→middle-MCP distance).
- Camera frames are processed **un-mirrored**; only the preview window is flipped for display.
- Scroll direction is natural: fingers move up → wheel delta negative (content moves up); fingers move down → positive.
- Every threshold comes from `Settings`; defaults are exactly the values in spec §6.
- Run tests with `uv run pytest -q`. Every task ends with all tests passing.
- Commit after every task. Every commit message ends with the trailer `Co-authored-by: Claude Fable 5.1 <noreply@anthropic.com>` (Julien's choice on 2026-09-23: co-authored commits in merged pull requests earn the GitHub Pair Extraordinaire badge).
- The Bash tool on this machine breaks on apostrophes inside heredocs. Create files with the Write tool, not shell heredocs.

---

## File structure

| File | Responsibility |
|---|---|
| `pyproject.toml` | uv project, deps, `handcontrol` / `handcontrol-gui` entry points, pytest config |
| `.gitignore` | venv, caches, logs, downloaded model |
| `handcontrol/__init__.py` | `__version__` |
| `handcontrol/__main__.py` | CLI parsing, logging setup (file log under pythonw), builds `App` |
| `handcontrol/config.py` | frozen `Settings` dataclasses with defaults; `load_settings()` with TOML override |
| `handcontrol/hand.py` | landmark indices, `RawHand`, `HandPose`, `pose_from_raw()`; pure geometry |
| `handcontrol/actions.py` | `OpenStartMenu`, `Scroll` action types; `InputBackend` protocol; `ActionExecutor` |
| `handcontrol/gestures/__init__.py` | empty |
| `handcontrol/gestures/base.py` | `Gesture` protocol, `GestureEngine` (priority + mutual exclusion) |
| `handcontrol/gestures/start_menu.py` | `StartMenuSwipe` state machine |
| `handcontrol/gestures/two_finger_scroll.py` | `TwoFingerScroll` state machine with notch accumulator |
| `handcontrol/winput.py` | ctypes `SendInput`, cursor and foreground-window helpers (Windows only) |
| `handcontrol/camera.py` | `Camera`: lazy open, read, release, reopen on failure |
| `handcontrol/tracker.py` | `HandTracker`: MediaPipe `HandLandmarker` in VIDEO mode → `list[RawHand]` |
| `handcontrol/model.py` | `ensure_model()`: download `hand_landmarker.task` if missing |
| `handcontrol/preview.py` | `Preview`: OpenCV debug window with landmarks and state text |
| `handcontrol/tray.py` | `Tray`: pystray icon/menu; `make_icon()` |
| `handcontrol/app.py` | `App`: lifecycle, tray callbacks, pipeline thread |
| `tests/handbuilder.py` | `build_hand()`: synthetic `RawHand` for any finger combination |
| `tests/test_*.py` | one test module per pure module (listed per task) |
| `README.md` | usage, gestures, configuration |

---

### Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `handcontrol/__init__.py`
- Create: `handcontrol/__main__.py` (placeholder, replaced in Task 11)

**Interfaces:**
- Produces: importable package `handcontrol` with `__version__ = "0.1.0"`; `uv run pytest` and `uv run handcontrol` work.

- [x] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "handcontrol"
version = "0.1.0"
description = "Control Windows with your hands: MediaPipe hand gestures from a system tray app"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "mediapipe>=1.0.1,<2",
    "opencv-python>=4.10",
    "numpy>=1.26",
    "pystray>=0.19.5",
    "pillow>=10",
]

[project.scripts]
handcontrol = "handcontrol.__main__:main"

[project.gui-scripts]
handcontrol-gui = "handcontrol.__main__:main"

[dependency-groups]
dev = ["pytest>=8"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["handcontrol"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [x] **Step 2: Write `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
*.log
*.task
*.part
```

- [x] **Step 3: Write `handcontrol/__init__.py`**

```python
"""HandControl: control Windows with hand gestures seen by the webcam."""

__version__ = "0.1.0"
```

- [x] **Step 4: Write the placeholder `handcontrol/__main__.py`**

```python
"""Placeholder entry point; replaced by the real CLI in Task 11."""

from handcontrol import __version__


def main(argv: list[str] | None = None) -> int:
    print(f"handcontrol {__version__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [x] **Step 5: Install and smoke-test**

Run: `uv sync`
Expected: creates `.venv` and `uv.lock`; resolves mediapipe 1.0.1, opencv-python, pystray, pillow, pytest without errors.

Run: `uv run handcontrol`
Expected: prints `handcontrol 0.1.0`.

Run: `uv run python -c "import mediapipe, cv2, pystray; from mediapipe.tasks.python import vision; print(mediapipe.__version__)"`
Expected: prints `1.0.1` (MediaPipe log lines on stderr are fine).

- [x] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock .gitignore handcontrol/__init__.py handcontrol/__main__.py
git commit -m "chore: scaffold uv project with mediapipe, opencv, pystray"
```

---

### Task 2: Settings with TOML override

**Files:**
- Create: `handcontrol/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces:
  - `CameraSettings(index=0, width=1280, height=720)`
  - `TrackerSettings(min_hand_detection_confidence=0.5, min_hand_presence_confidence=0.5, min_tracking_confidence=0.5)`
  - `HandSettings(finger_extended_angle_deg=150.0, fingers_joined_max_m=0.03)`
  - `StartMenuSettings(swipe_distance_palms=1.5, swipe_window_s=0.5, swipe_cooldown_s=1.5)`
  - `ScrollSettings(engage_frames=3, release_frames=5, deadzone_palms=0.02, gain_notches_per_palm=4.0, smoothing=0.5, wheel_step=120)`
  - `Settings(camera, tracker, hand, start_menu, scroll)` — all frozen dataclasses
  - `settings_from_dict(data: dict) -> Settings`
  - `load_settings(path: Path | None = None) -> Settings`
  - `app_data_dir() -> Path` (`%LOCALAPPDATA%\HandControl`), `default_config_path() -> Path`

- [x] **Step 1: Write the failing tests**

`tests/test_config.py`:

```python
from handcontrol.config import Settings, load_settings, settings_from_dict


def test_defaults_match_spec():
    s = Settings()
    assert (s.camera.index, s.camera.width, s.camera.height) == (0, 1280, 720)
    assert s.tracker.min_hand_detection_confidence == 0.5
    assert s.hand.finger_extended_angle_deg == 150.0
    assert s.hand.fingers_joined_max_m == 0.03
    assert (s.start_menu.swipe_distance_palms, s.start_menu.swipe_window_s, s.start_menu.swipe_cooldown_s) == (1.5, 0.5, 1.5)
    assert s.scroll.engage_frames == 3
    assert s.scroll.release_frames == 5
    assert s.scroll.deadzone_palms == 0.02
    assert s.scroll.gain_notches_per_palm == 4.0
    assert s.scroll.smoothing == 0.5
    assert s.scroll.wheel_step == 120


def test_partial_override_keeps_other_defaults():
    s = settings_from_dict({"scroll": {"gain_notches_per_palm": 8.0}, "camera": {"index": 2}})
    assert s.scroll.gain_notches_per_palm == 8.0
    assert s.scroll.wheel_step == 120
    assert s.camera.index == 2
    assert s.camera.width == 1280


def test_unknown_keys_and_sections_are_ignored():
    s = settings_from_dict({"scroll": {"bogus": 1}, "nonsense": {"a": 1}})
    assert s == Settings()


def test_non_table_section_is_ignored():
    assert settings_from_dict({"scroll": 5}) == Settings()


def test_missing_file_gives_defaults(tmp_path):
    assert load_settings(tmp_path / "nope.toml") == Settings()


def test_file_override(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text("[start_menu]\nswipe_cooldown_s = 3.0\n", encoding="utf-8")
    assert load_settings(p).start_menu.swipe_cooldown_s == 3.0


def test_malformed_file_falls_back_to_defaults(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text("[start_menu\nthis is not toml", encoding="utf-8")
    assert load_settings(p) == Settings()
```

- [x] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_config.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'handcontrol.config'`.

- [x] **Step 3: Write `handcontrol/config.py`**

```python
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
```

- [x] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_config.py -q`
Expected: `7 passed`.

- [x] **Step 5: Commit**

```bash
git add handcontrol/config.py tests/test_config.py
git commit -m "feat: settings dataclasses with TOML override"
```

---

### Task 3: Hand pose geometry

**Files:**
- Create: `handcontrol/hand.py`
- Create: `tests/handbuilder.py`
- Test: `tests/test_hand.py`

**Interfaces:**
- Consumes: `HandSettings` from Task 2.
- Produces:
  - `Point3 = tuple[float, float, float]`, `Point2 = tuple[float, float]`
  - landmark index constants `WRIST, THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP, INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP, MIDDLE_MCP, ..., PINKY_TIP`
  - `class Finger(Enum)`: `THUMB, INDEX, MIDDLE, RING, PINKY`
  - `RawHand(landmarks: list[Point3], world: list[Point3], handedness: str, score: float)` (frozen)
  - `HandPose(fingers: Mapping[Finger, bool], palm_facing_camera: bool, palm_size: float, palm_center: Point2, two_finger_point: Point2, two_fingers_joined: bool, t: float)` (frozen) with properties `is_open_palm` and `is_two_finger`
  - `pose_from_raw(raw: RawHand, t: float, settings: HandSettings) -> HandPose`
  - `angle_deg(a, b, c) -> float`, `finger_extended(world, finger, min_angle_deg) -> bool`, `palm_facing_camera(landmarks, handedness) -> bool`, `palm_size(landmarks) -> float`, `palm_center(landmarks) -> Point2`
  - test helper `build_hand(extended=ALL_FINGERS, *, spread=False, handedness="Right", facing=True, center=(0.5, 0.5)) -> RawHand`, whose palm size is exactly `0.1` image units, whose `palm_center` and `two_finger_point` move 1:1 with `center`.

- [x] **Step 1: Write the synthetic hand builder**

`tests/handbuilder.py`:

```python
"""Builds synthetic RawHand objects for unit tests (no camera, no MediaPipe).

World space is metres with the wrist at the origin; y grows downward like the
image, so the hand points "up" along -y and a curled finger folds toward +z.
Image landmarks are the world layout scaled by 1.25 around ``center``, so the
palm size (wrist -> middle MCP, 0.08 m) comes out at exactly 0.1 image units.

Handedness and mirroring: MediaPipe labels hands as seen in a selfie mirror,
where a "Right" hand with its palm toward the camera has the thumb on the
image LEFT. The builder puts the thumb at negative x and mirrors x whenever
the requested label/facing combination calls for it.
"""

from __future__ import annotations

from handcontrol.hand import Finger, RawHand

ALL_FINGERS = frozenset(Finger)

_MCP_X = {Finger.INDEX: -0.02, Finger.MIDDLE: 0.0, Finger.RING: 0.02, Finger.PINKY: 0.04}
_JOINTS = {
    Finger.INDEX: (5, 6, 7, 8),
    Finger.MIDDLE: (9, 10, 11, 12),
    Finger.RING: (13, 14, 15, 16),
    Finger.PINKY: (17, 18, 19, 20),
}
_UP = (0.0, -1.0, 0.0)
_FOLD = (0.0, 0.0, 1.0)


def _step(p, d, k):
    return (p[0] + d[0] * k, p[1] + d[1] * k, p[2] + d[2] * k)


def build_hand(
    extended: frozenset[Finger] | set[Finger] = ALL_FINGERS,
    *,
    spread: bool = False,
    handedness: str = "Right",
    facing: bool = True,
    center: tuple[float, float] = (0.5, 0.5),
) -> RawHand:
    world = [(0.0, 0.0, 0.0)] * 21
    # Thumb: CMC(1), MCP(2), IP(3), TIP(4). Extended = pointing up-left; curled = folded across the palm.
    world[1] = (-0.03, -0.02, 0.0)
    world[2] = (-0.05, -0.05, 0.0)
    thumb_dir = (-0.6, -0.8, 0.0) if Finger.THUMB in extended else (0.8, -0.2, 0.2)
    world[3] = _step(world[2], thumb_dir, 0.03)
    world[4] = _step(world[3], thumb_dir, 0.03)
    for finger, (mcp, pip, dip, tip) in _JOINTS.items():
        base = (_MCP_X[finger], -0.08, 0.0)
        proximal = _UP
        if spread and finger is Finger.INDEX:
            proximal = (-0.4, -0.9, 0.0)
        if spread and finger is Finger.MIDDLE:
            proximal = (0.4, -0.9, 0.0)
        distal = proximal if finger in extended else _FOLD  # curled: 90 degrees at the PIP joint
        world[mcp] = base
        world[pip] = _step(base, proximal, 0.03)
        world[dip] = _step(world[pip], distal, 0.025)
        world[tip] = _step(world[pip], distal, 0.05)
    mirror = (handedness == "Right") != facing
    sx = -1.25 if mirror else 1.25
    landmarks = [(center[0] + x * sx, center[1] + y * 1.25, z) for x, y, z in world]
    return RawHand(landmarks=landmarks, world=world, handedness=handedness, score=0.99)
```

- [x] **Step 2: Write the failing tests**

`tests/test_hand.py`:

```python
import pytest
from handbuilder import build_hand

from handcontrol.config import HandSettings
from handcontrol.hand import Finger, angle_deg, pose_from_raw

SETTINGS = HandSettings()


def pose(**kwargs):
    return pose_from_raw(build_hand(**kwargs), t=0.0, settings=SETTINGS)


def test_angle_straight_and_right_angle():
    assert angle_deg((0, 0, 0), (0, 1, 0), (0, 2, 0)) == pytest.approx(180.0)
    assert angle_deg((1, 0, 0), (0, 0, 0), (0, 1, 0)) == pytest.approx(90.0)


def test_degenerate_angle_is_zero():
    assert angle_deg((0, 0, 0), (0, 0, 0), (1, 0, 0)) == 0.0


def test_open_palm_has_all_fingers_extended():
    p = pose()
    assert all(p.fingers.values())
    assert p.palm_facing_camera
    assert p.is_open_palm
    assert not p.is_two_finger


def test_fist_has_nothing_extended():
    p = pose(extended=set())
    assert not any(p.fingers.values())
    assert not p.is_open_palm
    assert not p.is_two_finger


def test_two_finger_pose():
    p = pose(extended={Finger.INDEX, Finger.MIDDLE})
    assert p.two_fingers_joined
    assert p.is_two_finger
    assert not p.is_open_palm


def test_two_finger_pose_ignores_thumb():
    assert pose(extended={Finger.THUMB, Finger.INDEX, Finger.MIDDLE}).is_two_finger


def test_spread_fingers_are_not_joined():
    p = pose(extended={Finger.INDEX, Finger.MIDDLE}, spread=True)
    assert not p.two_fingers_joined
    assert not p.is_two_finger


def test_open_palm_requires_palm_facing_camera():
    p = pose(facing=False)
    assert not p.palm_facing_camera
    assert not p.is_open_palm


def test_open_palm_ignores_thumb():
    assert pose(extended={Finger.INDEX, Finger.MIDDLE, Finger.RING, Finger.PINKY}).is_open_palm


@pytest.mark.parametrize("handedness", ["Left", "Right"])
def test_facing_rule_holds_for_both_hands(handedness):
    assert pose(handedness=handedness, facing=True).palm_facing_camera
    assert not pose(handedness=handedness, facing=False).palm_facing_camera


def test_palm_size_is_distance_invariant_and_points_follow_the_hand():
    a = pose(center=(0.5, 0.5))
    b = pose(center=(0.5, 0.3))
    assert a.palm_size == pytest.approx(0.1)
    assert b.palm_size == pytest.approx(0.1)
    assert a.palm_center[1] - b.palm_center[1] == pytest.approx(0.2)
    assert a.two_finger_point[1] - b.two_finger_point[1] == pytest.approx(0.2)


def test_pose_carries_timestamp():
    assert pose_from_raw(build_hand(), t=12.5, settings=SETTINGS).t == 12.5
```

- [x] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/test_hand.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'handcontrol.hand'`.

- [x] **Step 4: Write `handcontrol/hand.py`**

```python
"""Pure geometry: turn 21 MediaPipe hand landmarks into a HandPose.

Landmark indices follow MediaPipe: 0 wrist; thumb 1-4 (CMC, MCP, IP, TIP);
index 5-8, middle 9-12, ring 13-16, pinky 17-20 (MCP, PIP, DIP, TIP).
Image landmarks are normalized 0..1 with y growing downward. World landmarks
are metres, centred on the hand, and are used for anything that must not
depend on distance or camera angle (finger bend, fingertip spacing).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from handcontrol.config import HandSettings

Point3 = tuple[float, float, float]
Point2 = tuple[float, float]

WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20


class Finger(Enum):
    THUMB = "thumb"
    INDEX = "index"
    MIDDLE = "middle"
    RING = "ring"
    PINKY = "pinky"


# (root, bending joint, tip): the angle at the bending joint says whether the finger is straight.
FINGER_JOINTS: dict[Finger, tuple[int, int, int]] = {
    Finger.THUMB: (THUMB_CMC, THUMB_MCP, THUMB_TIP),
    Finger.INDEX: (INDEX_MCP, INDEX_PIP, INDEX_TIP),
    Finger.MIDDLE: (MIDDLE_MCP, MIDDLE_PIP, MIDDLE_TIP),
    Finger.RING: (RING_MCP, RING_PIP, RING_TIP),
    Finger.PINKY: (PINKY_MCP, PINKY_PIP, PINKY_TIP),
}

FOUR_FINGERS = (Finger.INDEX, Finger.MIDDLE, Finger.RING, Finger.PINKY)


@dataclass(frozen=True)
class RawHand:
    landmarks: list[Point3]
    world: list[Point3]
    handedness: str
    score: float


@dataclass(frozen=True)
class HandPose:
    fingers: Mapping[Finger, bool]
    palm_facing_camera: bool
    palm_size: float
    palm_center: Point2
    two_finger_point: Point2
    two_fingers_joined: bool
    t: float

    @property
    def is_open_palm(self) -> bool:
        """Index..pinky extended and palm toward the camera. The thumb is ignored on purpose."""
        return self.palm_facing_camera and all(self.fingers[f] for f in FOUR_FINGERS)

    @property
    def is_two_finger(self) -> bool:
        return (
            self.fingers[Finger.INDEX]
            and self.fingers[Finger.MIDDLE]
            and self.two_fingers_joined
            and not self.fingers[Finger.RING]
            and not self.fingers[Finger.PINKY]
        )


def distance(a, b) -> float:
    return math.dist(a, b)


def angle_deg(a: Point3, b: Point3, c: Point3) -> float:
    """Angle at ``b`` in degrees between rays b->a and b->c; 180 means straight."""
    bax, bay, baz = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    bcx, bcy, bcz = c[0] - b[0], c[1] - b[1], c[2] - b[2]
    na = math.sqrt(bax * bax + bay * bay + baz * baz)
    nc = math.sqrt(bcx * bcx + bcy * bcy + bcz * bcz)
    if na == 0.0 or nc == 0.0:
        return 0.0
    cos = (bax * bcx + bay * bcy + baz * bcz) / (na * nc)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


def finger_extended(world: list[Point3], finger: Finger, min_angle_deg: float) -> bool:
    root, joint, tip = FINGER_JOINTS[finger]
    return angle_deg(world[root], world[joint], world[tip]) >= min_angle_deg


def palm_facing_camera(landmarks: list[Point3], handedness: str) -> bool:
    """True when the palm, not the back of the hand, faces the camera.

    Uses the 2-D cross product of wrist->index_mcp and wrist->pinky_mcp in
    image space (y down). MediaPipe labels hands as seen in a selfie mirror:
    a "Right" hand with the palm toward the camera shows its thumb on the
    image LEFT, so index_mcp sits left of pinky_mcp and the cross product is
    positive. The back of the hand flips the sign, and a "Left" hand flips it
    again. The rule holds whether or not the frame is actually mirrored,
    because the label flips together with the image. Confirmed on real frames
    in the preview window (Task 12).
    """
    w, i, p = landmarks[WRIST], landmarks[INDEX_MCP], landmarks[PINKY_MCP]
    ux, uy = i[0] - w[0], i[1] - w[1]
    vx, vy = p[0] - w[0], p[1] - w[1]
    z = ux * vy - uy * vx
    return z > 0 if handedness == "Right" else z < 0


def palm_size(landmarks: list[Point3]) -> float:
    """Image-space wrist -> middle MCP distance; the unit for all motion thresholds."""
    return distance(landmarks[WRIST][:2], landmarks[MIDDLE_MCP][:2])


def palm_center(landmarks: list[Point3]) -> Point2:
    idx = (WRIST, INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP)
    return (sum(landmarks[i][0] for i in idx) / 5, sum(landmarks[i][1] for i in idx) / 5)


def pose_from_raw(raw: RawHand, t: float, settings: HandSettings) -> HandPose:
    fingers = {f: finger_extended(raw.world, f, settings.finger_extended_angle_deg) for f in Finger}
    index_tip, middle_tip = raw.landmarks[INDEX_TIP], raw.landmarks[MIDDLE_TIP]
    return HandPose(
        fingers=fingers,
        palm_facing_camera=palm_facing_camera(raw.landmarks, raw.handedness),
        palm_size=palm_size(raw.landmarks),
        palm_center=palm_center(raw.landmarks),
        two_finger_point=((index_tip[0] + middle_tip[0]) / 2, (index_tip[1] + middle_tip[1]) / 2),
        two_fingers_joined=distance(raw.world[INDEX_TIP], raw.world[MIDDLE_TIP]) <= settings.fingers_joined_max_m,
        t=t,
    )
```

- [x] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_hand.py -q`
Expected: `13 passed`.

- [x] **Step 6: Commit**

```bash
git add handcontrol/hand.py tests/handbuilder.py tests/test_hand.py
git commit -m "feat: hand pose geometry from MediaPipe landmarks"
```

---

### Task 4: Action types and gesture engine

**Files:**
- Create: `handcontrol/actions.py` (types only; the executor is added in Task 7)
- Create: `handcontrol/gestures/__init__.py` (empty)
- Create: `handcontrol/gestures/base.py`
- Test: `tests/test_gesture_engine.py`

**Interfaces:**
- Consumes: `HandPose` from Task 3.
- Produces:
  - `OpenStartMenu()` and `Scroll(notches: int)` frozen dataclasses; `Action = OpenStartMenu | Scroll`
  - `Gesture` protocol: attributes `name: str`, `state: str`; property `engaged: bool`; `update(pose: HandPose | None, t: float) -> list[Action]`; `reset() -> None`
  - `GestureEngine(gestures: Sequence[Gesture])` with `update(pose, t) -> list[Action]`, `reset()`, property `states -> dict[str, str]`

- [x] **Step 1: Write the failing tests**

`tests/test_gesture_engine.py`:

```python
from handbuilder import build_hand

from handcontrol.actions import Scroll
from handcontrol.config import HandSettings
from handcontrol.gestures.base import GestureEngine
from handcontrol.hand import pose_from_raw

POSE = pose_from_raw(build_hand(), t=0.0, settings=HandSettings())


class FakeGesture:
    """Engages on the first non-None pose (if allowed) and emits Scroll(1) while engaged."""

    def __init__(self, name, engages=False):
        self.name = name
        self.engages = engages
        self.state = "IDLE"
        self._engaged = False
        self.seen = []
        self.resets = 0

    @property
    def engaged(self):
        return self._engaged

    def update(self, pose, t):
        self.seen.append(pose)
        if self.engages and pose is not None:
            self._engaged = True
            self.state = "ENGAGED"
        return [Scroll(1)] if self._engaged else []

    def reset(self):
        self._engaged = False
        self.state = "IDLE"
        self.resets += 1


def test_every_gesture_sees_the_pose_when_nobody_is_engaged():
    a, b = FakeGesture("a"), FakeGesture("b")
    assert GestureEngine([a, b]).update(POSE, 0.0) == []
    assert a.seen == [POSE] and b.seen == [POSE]


def test_newly_engaged_gesture_starves_lower_priority_in_the_same_frame():
    a, b = FakeGesture("a", engages=True), FakeGesture("b")
    engine = GestureEngine([a, b])
    assert engine.update(POSE, 0.0) == [Scroll(1)]
    assert b.seen == [] and b.resets == 1


def test_engaged_lower_priority_gesture_starves_higher_priority():
    a, b = FakeGesture("a"), FakeGesture("b", engages=True)
    engine = GestureEngine([a, b])
    engine.update(POSE, 0.0)          # both run; b engages at the end of the frame
    engine.update(POSE, 0.1)          # b owns the hand now
    assert a.seen == [POSE] and a.resets == 1
    assert len(b.seen) == 2


def test_states_and_reset():
    a, b = FakeGesture("a", engages=True), FakeGesture("b")
    engine = GestureEngine([a, b])
    engine.update(POSE, 0.0)
    assert engine.states == {"a": "ENGAGED", "b": "IDLE"}
    engine.reset()
    assert engine.states == {"a": "IDLE", "b": "IDLE"}
    assert not a.engaged
```

- [x] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_gesture_engine.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'handcontrol.actions'`.

- [x] **Step 3: Write `handcontrol/actions.py` (types only for now)**

```python
"""Actions produced by gestures. The executor that performs them lives here too (Task 7)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OpenStartMenu:
    """Press and release the Windows key."""


@dataclass(frozen=True)
class Scroll:
    """Mouse-wheel scroll by ``notches``; positive = wheel up (content moves down)."""

    notches: int


Action = OpenStartMenu | Scroll
```

- [x] **Step 4: Write `handcontrol/gestures/__init__.py` (empty file) and `handcontrol/gestures/base.py`**

```python
"""Gesture protocol and the engine that arbitrates between gestures."""

from __future__ import annotations

from typing import Protocol, Sequence

from handcontrol.actions import Action
from handcontrol.hand import HandPose


class Gesture(Protocol):
    name: str
    state: str

    @property
    def engaged(self) -> bool: ...

    def update(self, pose: HandPose | None, t: float) -> list[Action]: ...

    def reset(self) -> None: ...


class GestureEngine:
    """Runs gestures in priority order. An engaged gesture owns the hand: every
    other gesture is reset and skipped until it lets go."""

    def __init__(self, gestures: Sequence[Gesture]) -> None:
        self.gestures = list(gestures)

    def update(self, pose: HandPose | None, t: float) -> list[Action]:
        owner = next((g for g in self.gestures if g.engaged), None)
        actions: list[Action] = []
        for gesture in self.gestures:
            if owner is not None and gesture is not owner:
                gesture.reset()
                continue
            actions.extend(gesture.update(pose, t))
            if owner is None and gesture.engaged:
                owner = gesture
        return actions

    def reset(self) -> None:
        for gesture in self.gestures:
            gesture.reset()

    @property
    def states(self) -> dict[str, str]:
        return {g.name: g.state for g in self.gestures}
```

- [x] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_gesture_engine.py -q`
Expected: `4 passed`.

- [x] **Step 6: Commit**

```bash
git add handcontrol/actions.py handcontrol/gestures/__init__.py handcontrol/gestures/base.py tests/test_gesture_engine.py
git commit -m "feat: action types and gesture engine with mutual exclusion"
```

---

### Task 5: Start-menu swipe gesture

**Files:**
- Create: `handcontrol/gestures/start_menu.py`
- Test: `tests/test_start_menu.py`

**Interfaces:**
- Consumes: `StartMenuSettings` (Task 2), `HandPose.is_open_palm`, `palm_center`, `palm_size` (Task 3), `OpenStartMenu` (Task 4).
- Produces: `StartMenuSwipe(settings: StartMenuSettings)` implementing `Gesture`; `name == "start_menu"`; states `IDLE`, `ARMED`, `COOLDOWN`; `engaged` is true only in `ARMED`.

- [x] **Step 1: Write the failing tests**

`tests/test_start_menu.py`:

```python
from handbuilder import build_hand

from handcontrol.actions import OpenStartMenu
from handcontrol.config import HandSettings, StartMenuSettings
from handcontrol.gestures.start_menu import StartMenuSwipe
from handcontrol.hand import Finger, pose_from_raw

FPS = 30.0
HAND = HandSettings()


def open_palm(y, x=0.5):
    return pose_from_raw(build_hand(center=(x, y)), 0.0, HAND)


def two_finger(y):
    return pose_from_raw(build_hand(extended={Finger.INDEX, Finger.MIDDLE}, center=(0.5, y)), 0.0, HAND)


def run(gesture, poses, t0=0.0):
    """Feed poses at 30 fps starting at t0; return all emitted actions."""
    actions = []
    for i, p in enumerate(poses):
        actions.extend(gesture.update(p, t0 + i / FPS))
    return actions


def rising(y0, y1, frames, make=open_palm):
    return [make(y0 + (y1 - y0) * i / (frames - 1)) for i in range(frames)]


def test_fast_upward_sweep_fires_exactly_once():
    g = StartMenuSwipe(StartMenuSettings())
    # 3 palms up in 0.3 s, then hold: fires once, cooldown blocks the rest.
    actions = run(g, rising(0.7, 0.4, 9) + [open_palm(0.4)] * 15)
    assert actions == [OpenStartMenu()]
    assert g.state == "COOLDOWN"


def test_second_sweep_after_cooldown_fires_again():
    g = StartMenuSwipe(StartMenuSettings())
    first = run(g, rising(0.7, 0.4, 9))
    idle = run(g, [None] * 60, t0=1.0)          # 2 s away: cooldown over, hand gone
    second = run(g, rising(0.7, 0.4, 9), t0=3.0)
    assert first == [OpenStartMenu()] and idle == [] and second == [OpenStartMenu()]


def test_slow_drift_does_not_fire():
    g = StartMenuSwipe(StartMenuSettings())
    assert run(g, rising(0.7, 0.4, 61)) == []     # 3 palms over 2 s: never 1.5 palms inside 0.5 s


def test_downward_and_sideways_motion_do_not_fire():
    assert run(StartMenuSwipe(StartMenuSettings()), rising(0.4, 0.7, 9)) == []
    sideways = [open_palm(0.5, x=0.2 + 0.05 * i) for i in range(9)]
    assert run(StartMenuSwipe(StartMenuSettings()), sideways) == []


def test_non_open_palm_does_not_fire():
    g = StartMenuSwipe(StartMenuSettings())
    assert run(g, rising(0.7, 0.4, 9, make=two_finger)) == []
    assert not g.engaged


def test_open_palm_arms_and_losing_it_disarms():
    g = StartMenuSwipe(StartMenuSettings())
    run(g, [open_palm(0.5)] * 3)
    assert g.engaged and g.state == "ARMED"
    run(g, [None], t0=0.1)
    assert not g.engaged and g.state == "IDLE"


def test_rise_split_by_hand_loss_does_not_add_up():
    g = StartMenuSwipe(StartMenuSettings())
    a = run(g, rising(0.7, 0.6, 4))                 # 1 palm
    b = run(g, [None], t0=0.2)
    c = run(g, rising(0.6, 0.5, 4), t0=0.25)        # another 1 palm, new window
    assert a == b == c == []


def test_threshold_scales_with_palm_size():
    # Same image-space rise (0.12) is 1.2 palms at palm size 0.1 (no fire) ...
    g = StartMenuSwipe(StartMenuSettings(swipe_distance_palms=1.0))
    assert run(g, rising(0.62, 0.5, 6)) == [OpenStartMenu()]
    g2 = StartMenuSwipe(StartMenuSettings(swipe_distance_palms=1.5))
    assert run(g2, rising(0.62, 0.5, 6)) == []
```

- [x] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_start_menu.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'handcontrol.gestures.start_menu'`.

- [x] **Step 3: Write `handcontrol/gestures/start_menu.py`**

```python
"""Open palm facing the camera, swept upward -> OpenStartMenu."""

from __future__ import annotations

from collections import deque

from handcontrol.actions import Action, OpenStartMenu
from handcontrol.config import StartMenuSettings
from handcontrol.hand import HandPose


class StartMenuSwipe:
    name = "start_menu"

    def __init__(self, settings: StartMenuSettings) -> None:
        self.settings = settings
        self.state = "IDLE"
        self._samples: deque[tuple[float, float]] = deque()  # (t, palm centre y) inside the window
        self._cooldown_until = 0.0

    @property
    def engaged(self) -> bool:
        return self.state == "ARMED"

    def reset(self) -> None:
        self.state = "IDLE"
        self._samples.clear()

    def update(self, pose: HandPose | None, t: float) -> list[Action]:
        if self.state == "COOLDOWN":
            if t < self._cooldown_until:
                return []
            self.state = "IDLE"
        if pose is None or not pose.is_open_palm:
            self.reset()
            return []
        self.state = "ARMED"
        y = pose.palm_center[1]
        self._samples.append((t, y))
        while self._samples and t - self._samples[0][0] > self.settings.swipe_window_s:
            self._samples.popleft()
        lowest_y = max(sample_y for _, sample_y in self._samples)  # y grows downward
        if lowest_y - y >= self.settings.swipe_distance_palms * pose.palm_size:
            self.state = "COOLDOWN"
            self._cooldown_until = t + self.settings.swipe_cooldown_s
            self._samples.clear()
            return [OpenStartMenu()]
        return []
```

- [x] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_start_menu.py -q`
Expected: `8 passed`.

- [x] **Step 5: Commit**

```bash
git add handcontrol/gestures/start_menu.py tests/test_start_menu.py
git commit -m "feat: start-menu open-palm swipe gesture"
```

---

### Task 6: Two-finger scroll gesture

**Files:**
- Create: `handcontrol/gestures/two_finger_scroll.py`
- Test: `tests/test_two_finger_scroll.py`

**Interfaces:**
- Consumes: `ScrollSettings` (Task 2), `HandPose.is_two_finger`, `two_finger_point`, `palm_size` (Task 3), `Scroll` (Task 4), `GestureEngine` and `StartMenuSwipe` for the arbitration test.
- Produces: `TwoFingerScroll(settings: ScrollSettings)` implementing `Gesture`; `name == "scroll"`; states `IDLE`, `TRACKING`; `engaged` true while `TRACKING`.

- [x] **Step 1: Write the failing tests**

`tests/test_two_finger_scroll.py`:

```python
from handbuilder import build_hand

from handcontrol.actions import OpenStartMenu, Scroll
from handcontrol.config import HandSettings, ScrollSettings, StartMenuSettings
from handcontrol.gestures.base import GestureEngine
from handcontrol.gestures.start_menu import StartMenuSwipe
from handcontrol.gestures.two_finger_scroll import TwoFingerScroll
from handcontrol.hand import Finger, pose_from_raw

FPS = 30.0
HAND = HandSettings()
EXACT = ScrollSettings(smoothing=0.0, deadzone_palms=0.0)  # deterministic: no EMA, no dead zone
PALM = 0.1  # build_hand palm size in image units


def two_finger(y):
    return pose_from_raw(build_hand(extended={Finger.INDEX, Finger.MIDDLE}, center=(0.5, y)), 0.0, HAND)


def open_palm(y):
    return pose_from_raw(build_hand(center=(0.5, y)), 0.0, HAND)


def run(gesture, poses, t0=0.0):
    actions = []
    for i, p in enumerate(poses):
        actions.extend(gesture.update(p, t0 + i / FPS))
    return actions


def moving(y0, step, frames):
    """Two-finger poses starting one step after y0, moving by ``step`` per frame."""
    return [two_finger(y0 + step * i) for i in range(1, frames + 1)]


def total(actions):
    assert all(isinstance(a, Scroll) for a in actions)
    return sum(a.notches for a in actions)


def engaged_gesture(settings=EXACT, y=0.6):
    g = TwoFingerScroll(settings)
    run(g, [two_finger(y)] * settings.engage_frames)
    assert g.engaged
    return g


def test_needs_engage_frames_before_tracking():
    g = TwoFingerScroll(EXACT)
    run(g, [two_finger(0.5)] * 2)
    assert not g.engaged and g.state == "IDLE"
    run(g, [two_finger(0.5)], t0=0.1)
    assert g.engaged and g.state == "TRACKING"


def test_hold_must_be_consecutive():
    g = TwoFingerScroll(EXACT)
    run(g, [two_finger(0.5), two_finger(0.5), None, two_finger(0.5), two_finger(0.5)])
    assert not g.engaged


def test_moving_up_scrolls_down_natural_direction():
    g = engaged_gesture()
    # 0.1 palm per frame upward (y decreasing), gain 4 -> 0.4 notch/frame.
    assert total(run(g, moving(0.6, -0.1 * PALM, 9), t0=1.0)) == -3     # 3.6 -> 3 emitted
    assert total(run(g, moving(0.6 - 0.9 * PALM, -0.1 * PALM, 2), t0=2.0)) == -1  # 4.4 total -> 4


def test_moving_down_scrolls_up():
    g = engaged_gesture(y=0.4)
    assert total(run(g, moving(0.4, 0.1 * PALM, 11), t0=1.0)) == 4


def test_fractional_remainder_carries_across_frames():
    g = engaged_gesture()
    # 0.15 palm per frame -> 0.6 notch per frame: acc -0.6, -1.2 (emit -1), -0.8, -1.4 (emit -1)
    per_frame = [total(g.update(p, 1.0 + i / FPS)) for i, p in enumerate(moving(0.6, -0.15 * PALM, 4))]
    assert per_frame == [0, -1, 0, -1]


def test_dead_zone_swallows_jitter():
    g = engaged_gesture(ScrollSettings(smoothing=0.0))   # default dead zone 0.02 palm
    jitter = [two_finger(0.6 + (0.0005 if i % 2 else -0.0005)) for i in range(30)]  # 0.01 palm/frame, under 0.02
    assert run(g, jitter, t0=1.0) == []


def test_default_smoothing_keeps_direction_and_magnitude_close():
    g = engaged_gesture(ScrollSettings())
    actions = run(g, moving(0.6, -0.1 * PALM, 11), t0=1.0)
    assert all(a.notches < 0 for a in actions)
    assert -4 <= total(actions) <= -2


def test_one_frame_flicker_keeps_tracking():
    g = engaged_gesture()
    g.update(None, 1.0)
    assert g.engaged
    assert total(run(g, moving(0.6, -0.1 * PALM, 11), t0=1.1)) == -4


def test_losing_the_hand_beyond_release_frames_resets():
    g = engaged_gesture()
    run(g, [None] * 5, t0=1.0)
    assert g.engaged
    run(g, [None], t0=1.2)
    assert not g.engaged and g.state == "IDLE"


def test_open_palm_is_not_a_scroll_pose():
    g = TwoFingerScroll(EXACT)
    run(g, [open_palm(0.5)] * 5)
    assert not g.engaged


def test_engine_scroll_in_progress_blocks_start_menu():
    engine = GestureEngine([TwoFingerScroll(EXACT), StartMenuSwipe(StartMenuSettings())])
    for i in range(3):
        engine.update(two_finger(0.6), i / FPS)
    assert engine.states["scroll"] == "TRACKING"
    # Switch straight to a fast open-palm sweep during the scroll release window.
    actions = []
    for i in range(5):
        actions.extend(engine.update(open_palm(0.7 - 0.075 * i), 0.1 + i / FPS))
    assert OpenStartMenu() not in actions
```

- [x] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_two_finger_scroll.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'handcontrol.gestures.two_finger_scroll'`.

- [x] **Step 3: Write `handcontrol/gestures/two_finger_scroll.py`**

```python
"""Index + middle finger joined, moved vertically -> Scroll (natural direction)."""

from __future__ import annotations

from handcontrol.actions import Action, Scroll
from handcontrol.config import ScrollSettings
from handcontrol.hand import HandPose


class TwoFingerScroll:
    name = "scroll"

    def __init__(self, settings: ScrollSettings) -> None:
        self.settings = settings
        self.state = "IDLE"
        self._held_frames = 0
        self._missing_frames = 0
        self._prev_y = 0.0
        self._velocity = 0.0      # smoothed, palm units per frame, positive = fingers moving down
        self._notches_acc = 0.0   # fractional wheel notches not yet emitted

    @property
    def engaged(self) -> bool:
        return self.state == "TRACKING"

    def reset(self) -> None:
        self.state = "IDLE"
        self._held_frames = 0
        self._missing_frames = 0
        self._velocity = 0.0
        self._notches_acc = 0.0

    def update(self, pose: HandPose | None, t: float) -> list[Action]:
        present = pose is not None and pose.is_two_finger
        if self.state == "IDLE":
            if not present:
                self._held_frames = 0
                return []
            self._held_frames += 1
            if self._held_frames >= self.settings.engage_frames:
                self.state = "TRACKING"
                self._prev_y = pose.two_finger_point[1]
                self._missing_frames = 0
                self._velocity = 0.0
                self._notches_acc = 0.0
            return []

        # TRACKING
        if not present:
            self._missing_frames += 1
            if self._missing_frames > self.settings.release_frames:
                self.reset()
            return []
        self._missing_frames = 0
        y = pose.two_finger_point[1]
        dy = (y - self._prev_y) / pose.palm_size
        self._prev_y = y
        s = self.settings.smoothing
        self._velocity = s * self._velocity + (1.0 - s) * dy
        if abs(self._velocity) < self.settings.deadzone_palms:
            return []
        # Fingers down (dy > 0) -> content moves down -> wheel up (positive). Natural scrolling.
        self._notches_acc += self._velocity * self.settings.gain_notches_per_palm
        notches = int(self._notches_acc)  # truncates toward zero, remainder stays in the accumulator
        if notches == 0:
            return []
        self._notches_acc -= notches
        return [Scroll(notches)]
```

- [x] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_two_finger_scroll.py -q`
Expected: `11 passed`.

- [x] **Step 5: Run the whole suite**

Run: `uv run pytest -q`
Expected: all tests pass (7 + 13 + 4 + 8 + 11 = 43).

- [x] **Step 6: Commit**

```bash
git add handcontrol/gestures/two_finger_scroll.py tests/test_two_finger_scroll.py
git commit -m "feat: two-finger natural scroll gesture"
```

---

### Task 7: Windows input injection and action executor

**Files:**
- Create: `handcontrol/winput.py`
- Modify: `handcontrol/actions.py` (append `InputBackend` and `ActionExecutor`)
- Test: `tests/test_actions.py`

**Interfaces:**
- Produces:
  - `winput.tap_key(vk: int)`, `winput.scroll_wheel(delta: int)`, `winput.cursor_pos() -> tuple[int, int]`, `winput.set_cursor_pos(x, y)`, `winput.foreground_window_rect() -> tuple[int, int, int, int] | None`, `winput.VK_LWIN`
  - `actions.VK_LWIN = 0x5B`
  - `actions.InputBackend` protocol with exactly those five functions (the `winput` module satisfies it)
  - `actions.ActionExecutor(backend: InputBackend, wheel_step: int = 120)` with `execute(action: Action) -> None`

- [x] **Step 1: Write the failing tests**

`tests/test_actions.py`:

```python
from handcontrol.actions import VK_LWIN, ActionExecutor, OpenStartMenu, Scroll


class FakeBackend:
    def __init__(self, cursor=(10, 10), rect=(0, 0, 100, 100)):
        self.cursor = cursor
        self.rect = rect
        self.calls = []

    def tap_key(self, vk):
        self.calls.append(("tap_key", vk))

    def scroll_wheel(self, delta):
        self.calls.append(("scroll_wheel", delta))

    def cursor_pos(self):
        return self.cursor

    def set_cursor_pos(self, x, y):
        self.cursor = (x, y)
        self.calls.append(("set_cursor_pos", x, y))

    def foreground_window_rect(self):
        return self.rect


def test_start_menu_taps_the_windows_key():
    b = FakeBackend()
    ActionExecutor(b).execute(OpenStartMenu())
    assert b.calls == [("tap_key", VK_LWIN)]
    assert VK_LWIN == 0x5B


def test_scroll_inside_foreground_window_only_sends_wheel():
    b = FakeBackend(cursor=(50, 50))
    ActionExecutor(b).execute(Scroll(2))
    assert b.calls == [("scroll_wheel", 240)]


def test_scroll_moves_cursor_into_foreground_window_first():
    b = FakeBackend(cursor=(500, 500), rect=(100, 200, 300, 400))
    ActionExecutor(b).execute(Scroll(-1))
    assert b.calls == [("set_cursor_pos", 200, 300), ("scroll_wheel", -120)]


def test_cursor_on_the_window_edge_counts_as_inside():
    b = FakeBackend(cursor=(0, 0))
    ActionExecutor(b).execute(Scroll(1))
    assert b.calls == [("scroll_wheel", 120)]


def test_no_foreground_window_scrolls_without_moving():
    b = FakeBackend(cursor=(500, 500), rect=None)
    ActionExecutor(b).execute(Scroll(1))
    assert b.calls == [("scroll_wheel", 120)]


def test_wheel_step_is_configurable():
    b = FakeBackend()
    ActionExecutor(b, wheel_step=40).execute(Scroll(3))
    assert b.calls == [("scroll_wheel", 120)]
```

- [x] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_actions.py -q`
Expected: FAIL with `ImportError: cannot import name 'VK_LWIN'`.

- [x] **Step 3: Append the backend protocol and executor to `handcontrol/actions.py`**

Add below `Action = OpenStartMenu | Scroll` (and add `from typing import Protocol` plus `import logging` to the imports):

```python
log = logging.getLogger(__name__)

VK_LWIN = 0x5B  # left Windows key virtual-key code


class InputBackend(Protocol):
    def tap_key(self, vk: int) -> None: ...

    def scroll_wheel(self, delta: int) -> None: ...

    def cursor_pos(self) -> tuple[int, int]: ...

    def set_cursor_pos(self, x: int, y: int) -> None: ...

    def foreground_window_rect(self) -> tuple[int, int, int, int] | None: ...


class ActionExecutor:
    """Performs actions through an InputBackend (the ``winput`` module in production)."""

    def __init__(self, backend: InputBackend, wheel_step: int = 120) -> None:
        self.backend = backend
        self.wheel_step = wheel_step

    def execute(self, action: Action) -> None:
        match action:
            case OpenStartMenu():
                self.backend.tap_key(VK_LWIN)
            case Scroll(notches):
                self._ensure_cursor_in_foreground_window()
                self.backend.scroll_wheel(notches * self.wheel_step)
            case _:
                log.warning("unknown action %r", action)

    def _ensure_cursor_in_foreground_window(self) -> None:
        """Windows delivers wheel events to the window under the cursor, so park the
        cursor inside the focused window when it is somewhere else."""
        rect = self.backend.foreground_window_rect()
        if rect is None:
            return
        left, top, right, bottom = rect
        x, y = self.backend.cursor_pos()
        if not (left <= x < right and top <= y < bottom):
            self.backend.set_cursor_pos((left + right) // 2, (top + bottom) // 2)
```

- [x] **Step 4: Write `handcontrol/winput.py`**

```python
"""Thin ctypes wrappers over user32 for input injection. Windows only."""

from __future__ import annotations

import ctypes
import logging
from ctypes import wintypes

log = logging.getLogger(__name__)

_user32 = ctypes.WinDLL("user32", use_last_error=True)

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_WHEEL = 0x0800
VK_LWIN = 0x5B
WHEEL_DELTA = 120

ULONG_PTR = ctypes.c_size_t


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


_user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
_user32.SendInput.restype = wintypes.UINT
_user32.GetCursorPos.argtypes = (ctypes.POINTER(wintypes.POINT),)
_user32.GetCursorPos.restype = wintypes.BOOL
_user32.SetCursorPos.argtypes = (ctypes.c_int, ctypes.c_int)
_user32.SetCursorPos.restype = wintypes.BOOL
_user32.GetForegroundWindow.restype = wintypes.HWND
_user32.GetWindowRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
_user32.GetWindowRect.restype = wintypes.BOOL


def _send(*inputs: INPUT) -> None:
    array = (INPUT * len(inputs))(*inputs)
    sent = _user32.SendInput(len(inputs), array, ctypes.sizeof(INPUT))
    if sent != len(inputs):
        log.warning("SendInput delivered %d of %d events (error %d)", sent, len(inputs), ctypes.get_last_error())


def tap_key(vk: int) -> None:
    """Press and release a virtual key."""
    down = INPUT(type=INPUT_KEYBOARD)
    down.ki.wVk = vk
    up = INPUT(type=INPUT_KEYBOARD)
    up.ki.wVk = vk
    up.ki.dwFlags = KEYEVENTF_KEYUP
    _send(down, up)


def scroll_wheel(delta: int) -> None:
    """Vertical wheel: +120 is one notch up (content moves down), -120 one notch down."""
    event = INPUT(type=INPUT_MOUSE)
    event.mi.mouseData = delta & 0xFFFFFFFF  # DWORD field carrying a signed value
    event.mi.dwFlags = MOUSEEVENTF_WHEEL
    _send(event)


def cursor_pos() -> tuple[int, int]:
    point = wintypes.POINT()
    _user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def set_cursor_pos(x: int, y: int) -> None:
    _user32.SetCursorPos(int(x), int(y))


def foreground_window_rect() -> tuple[int, int, int, int] | None:
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return None
    rect = wintypes.RECT()
    if not _user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    return rect.left, rect.top, rect.right, rect.bottom
```

- [x] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_actions.py -q`
Expected: `6 passed`.

- [x] **Step 6: Manually verify real injection**

Open a long web page or document, leave the mouse over it, and run:

```
uv run python -c "import time; from handcontrol import winput; time.sleep(3); winput.scroll_wheel(-360); time.sleep(1); winput.scroll_wheel(360)"
```

Expected: after 3 s the page scrolls down three notches, then back up.

Then run:

```
uv run python -c "import time; from handcontrol import winput; time.sleep(2); winput.tap_key(winput.VK_LWIN)"
```

Expected: the Start menu opens after 2 s. Press Escape to close it.

- [x] **Step 7: Commit**

```bash
git add handcontrol/winput.py handcontrol/actions.py tests/test_actions.py
git commit -m "feat: Windows input injection and action executor"
```

---

### Task 8: Camera, tracker and model download

**Files:**
- Create: `handcontrol/model.py`
- Create: `handcontrol/camera.py`
- Create: `handcontrol/tracker.py`
- Test: `tests/test_model.py`

**Interfaces:**
- Consumes: `TrackerSettings` (Task 2), `RawHand` (Task 3).
- Produces:
  - `model.MODEL_URL: str`; `model.ensure_model(path: Path, fetch=<urllib downloader>) -> Path` raising `OSError` on failure and leaving no partial file
  - `Camera(index: int, width: int, height: int)` with `read() -> np.ndarray | None` (BGR; opens lazily, releases itself on failure so the next `read` retries), `release()`, `is_open`
  - `HandTracker(model_path: Path, settings: TrackerSettings, num_hands: int = 1)` with `detect(frame_bgr, timestamp_ms: int) -> list[RawHand]` and `close()`

- [x] **Step 1: Write the failing tests**

`tests/test_model.py`:

```python
from pathlib import Path

import pytest

from handcontrol.model import MODEL_URL, ensure_model


def test_downloads_when_missing(tmp_path):
    target = tmp_path / "models" / "hand_landmarker.task"
    calls = []

    def fake_fetch(url, dest):
        calls.append((url, dest))
        Path(dest).write_bytes(b"model-bytes")

    assert ensure_model(target, fetch=fake_fetch) == target
    assert target.read_bytes() == b"model-bytes"
    assert calls == [(MODEL_URL, str(target.with_suffix(".task.part")))]


def test_skips_download_when_present(tmp_path):
    target = tmp_path / "hand_landmarker.task"
    target.write_bytes(b"existing")
    calls = []
    ensure_model(target, fetch=lambda url, dest: calls.append(url))
    assert calls == [] and target.read_bytes() == b"existing"


def test_failure_raises_oserror_and_leaves_no_partial_file(tmp_path):
    target = tmp_path / "hand_landmarker.task"

    def bad_fetch(url, dest):
        Path(dest).write_bytes(b"half")
        raise ConnectionError("network down")

    with pytest.raises(OSError, match="network down"):
        ensure_model(target, fetch=bad_fetch)
    assert not target.exists()
    assert list(tmp_path.iterdir()) == []
```

- [x] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_model.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'handcontrol.model'`.

- [x] **Step 3: Write `handcontrol/model.py`**

```python
"""Locate or download the MediaPipe hand landmarker model."""

from __future__ import annotations

import logging
import os
import urllib.request
from pathlib import Path
from typing import Callable

log = logging.getLogger(__name__)

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"

Fetch = Callable[[str, str], object]


def _download(url: str, dest: str) -> None:
    urllib.request.urlretrieve(url, dest)


def ensure_model(path: Path, fetch: Fetch = _download) -> Path:
    """Return ``path``, downloading the model there first if it is missing.

    Downloads to a ``.part`` file and renames on success so a failed download
    never leaves a truncated model behind. Raises OSError on any failure.
    """
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".part")
    log.info("downloading hand model to %s", path)
    try:
        fetch(MODEL_URL, str(part))
        os.replace(part, path)
    except Exception as exc:
        part.unlink(missing_ok=True)
        raise OSError(f"model download failed: {exc}") from exc
    return path
```

- [x] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_model.py -q`
Expected: `3 passed`.

- [x] **Step 5: Write `handcontrol/camera.py`**

```python
"""Webcam capture: lazy open, self-healing read, explicit release."""

from __future__ import annotations

import logging

import cv2
import numpy as np

log = logging.getLogger(__name__)


class Camera:
    def __init__(self, index: int, width: int, height: int) -> None:
        self.index = index
        self.width = width
        self.height = height
        self._cap: cv2.VideoCapture | None = None

    @property
    def is_open(self) -> bool:
        return self._cap is not None

    def open(self) -> bool:
        cap = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            log.warning("camera %d could not be opened", self.index)
            return False
        # MJPG lets DirectShow deliver 30 fps at 720p; raw YUY2 often drops to 5-10 fps.
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._cap = cap
        log.info(
            "camera %d open at %dx%d",
            self.index,
            int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )
        return True

    def read(self) -> np.ndarray | None:
        """Return a BGR frame, or None if the camera is unavailable (it will retry on the next call)."""
        if self._cap is None and not self.open():
            return None
        assert self._cap is not None
        ok, frame = self._cap.read()
        if not ok or frame is None:
            log.warning("camera %d read failed, releasing", self.index)
            self.release()
            return None
        return frame

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
```

- [x] **Step 6: Write `handcontrol/tracker.py`**

```python
"""MediaPipe HandLandmarker wrapper (Tasks API, VIDEO mode, synchronous, CPU)."""

from __future__ import annotations

from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

from handcontrol.config import TrackerSettings
from handcontrol.hand import RawHand


class HandTracker:
    def __init__(self, model_path: Path, settings: TrackerSettings, num_hands: int = 1) -> None:
        options = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=settings.min_hand_detection_confidence,
            min_hand_presence_confidence=settings.min_hand_presence_confidence,
            min_tracking_confidence=settings.min_tracking_confidence,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        self._last_timestamp_ms = -1

    def detect(self, frame_bgr: np.ndarray, timestamp_ms: int) -> list[RawHand]:
        # VIDEO mode requires strictly increasing timestamps.
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1
        self._last_timestamp_ms = timestamp_ms
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(image, timestamp_ms)
        return [
            RawHand(
                landmarks=[(p.x, p.y, p.z) for p in landmarks],
                world=[(p.x, p.y, p.z) for p in world],
                handedness=categories[0].category_name,
                score=categories[0].score,
            )
            for landmarks, world, categories in zip(
                result.hand_landmarks, result.hand_world_landmarks, result.handedness
            )
        ]

    def close(self) -> None:
        self._landmarker.close()
```

- [x] **Step 7: Manually verify capture and tracking together**

Write this throwaway script to the scratchpad directory as `check_tracker.py` (Write tool, not a heredoc):

```python
import logging
import time

from handcontrol.camera import Camera
from handcontrol.config import Settings, app_data_dir
from handcontrol.model import ensure_model
from handcontrol.tracker import HandTracker

logging.basicConfig(level=logging.INFO)
settings = Settings()
model = ensure_model(app_data_dir() / "models" / "hand_landmarker.task")
camera = Camera(settings.camera.index, settings.camera.width, settings.camera.height)
tracker = HandTracker(model, settings.tracker)
frames = seen = 0
t0 = time.monotonic()
while frames < 90:
    frame = camera.read()
    if frame is None:
        print("no frame")
        break
    frames += 1
    hands = tracker.detect(frame, int((time.monotonic() - t0) * 1000))
    if hands:
        seen += 1
        last = hands[0]
elapsed = time.monotonic() - t0
print(f"{frames} frames in {elapsed:.2f}s = {frames / elapsed:.1f} fps, hand seen in {seen}")
if seen:
    print("handedness:", last.handedness, "wrist:", last.landmarks[0])
camera.release()
tracker.close()
```

Sit in front of the webcam with one hand raised and run: `uv run python <scratchpad>/check_tracker.py`

Expected: the model downloads on first run to `%LOCALAPPDATA%\HandControl\models\`; then roughly `90 frames in 3.xs = 25-30 fps, hand seen in 80+` and a handedness line. If fps is below 15, check the camera log line for the negotiated resolution.

- [x] **Step 8: Commit**

```bash
git add handcontrol/model.py handcontrol/camera.py handcontrol/tracker.py tests/test_model.py
git commit -m "feat: camera capture, MediaPipe hand tracker and model download"
```

---

### Task 9: Preview window

**Files:**
- Create: `handcontrol/preview.py`

**Interfaces:**
- Consumes: `RawHand`, `HandPose`, `Finger` (Task 3).
- Produces: `Preview()` with `draw(frame_bgr, raw: RawHand | None, pose: HandPose | None, states: dict[str, str]) -> None`, `close() -> None`, attribute `is_open: bool`. Must be called from one thread only (OpenCV HighGUI rule).

- [x] **Step 1: Write `handcontrol/preview.py`**

```python
"""Debug preview window: landmarks on the mirrored frame, finger flags, gesture states, fps."""

from __future__ import annotations

import time

import cv2
import numpy as np

from handcontrol.hand import HandPose, RawHand

WINDOW = "HandControl preview"
CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]
GREEN = (80, 200, 80)
WHITE = (255, 255, 255)
YELLOW = (0, 220, 255)


class Preview:
    def __init__(self) -> None:
        self.is_open = False
        self._last_t = time.monotonic()
        self._fps = 0.0

    def draw(self, frame_bgr: np.ndarray, raw: RawHand | None, pose: HandPose | None, states: dict[str, str]) -> None:
        now = time.monotonic()
        dt = now - self._last_t
        self._last_t = now
        if dt > 0:
            self._fps = 0.9 * self._fps + 0.1 / dt

        img = frame_bgr.copy()
        h, w = img.shape[:2]
        if raw is not None:
            pts = [(int(x * w), int(y * h)) for x, y, _ in raw.landmarks]
            for a, b in CONNECTIONS:
                cv2.line(img, pts[a], pts[b], GREEN, 2)
            for p in pts:
                cv2.circle(img, p, 4, WHITE, -1)
        img = cv2.flip(img, 1)  # mirror for the viewer; text is drawn after the flip so it reads normally

        lines = [f"{self._fps:4.1f} fps"]
        if pose is None:
            lines.append("no hand")
        else:
            flags = " ".join(f.value[:2] + ("+" if on else "-") for f, on in pose.fingers.items())
            lines.append(flags)
            lines.append(f"facing={pose.palm_facing_camera} joined={pose.two_fingers_joined} palm={pose.palm_size:.3f}")
            lines.append(f"open_palm={pose.is_open_palm} two_finger={pose.is_two_finger}")
        lines.extend(f"{name}: {state}" for name, state in states.items())
        for i, text in enumerate(lines):
            cv2.putText(img, text, (10, 24 + 22 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.6, YELLOW, 2, cv2.LINE_AA)

        cv2.imshow(WINDOW, img)
        cv2.waitKey(1)
        self.is_open = True

    def close(self) -> None:
        if not self.is_open:
            return
        try:
            cv2.destroyWindow(WINDOW)
        except cv2.error:
            pass
        self.is_open = False
```

- [x] **Step 2: Verify it imports and the full suite still passes**

Run: `uv run python -c "from handcontrol.preview import Preview; print(Preview().is_open)"`
Expected: `False`.

Run: `uv run pytest -q`
Expected: all tests pass.

- [x] **Step 3: Commit**

```bash
git add handcontrol/preview.py
git commit -m "feat: debug preview window"
```

---

### Task 10: Tray icon

**Files:**
- Create: `handcontrol/tray.py`
- Test: `tests/test_tray.py`

**Interfaces:**
- Produces:
  - `State = Literal["running", "disabled", "error"]`
  - `make_icon(state: State, size: int = 64) -> PIL.Image.Image`
  - `Tray(*, on_enabled_changed: Callable[[bool], None], on_preview_changed: Callable[[bool], None], on_quit: Callable[[], None], preview: bool = False)` with `run(ready: Callable[[], None]) -> None` (blocks; calls `ready()` once the icon is visible), `stop()`, `set_state(state: State, text: str)`, `notify(message: str)`

- [x] **Step 1: Write the failing test**

`tests/test_tray.py`:

```python
from handcontrol.tray import make_icon


def test_icons_are_square_rgba_and_coloured_by_state():
    running, disabled, error = (make_icon(s) for s in ("running", "disabled", "error"))
    for img in (running, disabled, error):
        assert img.size == (64, 64) and img.mode == "RGBA"
        assert img.getpixel((0, 0))[3] == 0            # corner outside the disc is transparent
        assert img.getpixel((4, 32))[3] == 255         # left edge of the disc is painted
    assert len({running.getpixel((4, 32)), disabled.getpixel((4, 32)), error.getpixel((4, 32))}) == 3
```

- [x] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_tray.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'handcontrol.tray'`.

- [x] **Step 3: Write `handcontrol/tray.py`**

```python
"""System tray icon and menu (pystray). Runs on the main thread."""

from __future__ import annotations

import logging
from typing import Callable, Literal

import pystray
from PIL import Image, ImageDraw

log = logging.getLogger(__name__)

State = Literal["running", "disabled", "error"]

_COLORS: dict[str, tuple[int, int, int, int]] = {
    "running": (46, 160, 67, 255),
    "disabled": (128, 128, 128, 255),
    "error": (220, 53, 69, 255),
}


def make_icon(state: State, size: int = 64) -> Image.Image:
    """A coloured disc with a simple white hand glyph."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((0, 0, size - 1, size - 1), fill=_COLORS[state])
    u = size / 16
    d.rounded_rectangle((5 * u, 7 * u, 11 * u, 13 * u), radius=u, fill="white")  # palm
    for i in range(4):  # four fingers
        x = (5 + 1.5 * i) * u
        d.rounded_rectangle((x, 3 * u, x + u, 8 * u), radius=u / 2, fill="white")
    d.rounded_rectangle((3 * u, 7 * u, 5.5 * u, 8.5 * u), radius=u / 2, fill="white")  # thumb
    return img


class Tray:
    def __init__(
        self,
        *,
        on_enabled_changed: Callable[[bool], None],
        on_preview_changed: Callable[[bool], None],
        on_quit: Callable[[], None],
        preview: bool = False,
    ) -> None:
        self._enabled = True
        self._preview = preview
        self._on_enabled_changed = on_enabled_changed
        self._on_preview_changed = on_preview_changed
        self._on_quit = on_quit
        self._icon = pystray.Icon(
            "handcontrol",
            icon=make_icon("running"),
            title="HandControl - starting",
            menu=pystray.Menu(
                pystray.MenuItem("Enabled", self._toggle_enabled, checked=lambda item: self._enabled),
                pystray.MenuItem("Show preview", self._toggle_preview, checked=lambda item: self._preview),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", self._quit),
            ),
        )

    def _toggle_enabled(self, icon, item) -> None:
        self._enabled = not self._enabled
        self._on_enabled_changed(self._enabled)

    def _toggle_preview(self, icon, item) -> None:
        self._preview = not self._preview
        self._on_preview_changed(self._preview)

    def _quit(self, icon, item) -> None:
        self._on_quit()

    def set_state(self, state: State, text: str) -> None:
        self._icon.icon = make_icon(state)
        self._icon.title = f"HandControl - {text}"

    def notify(self, message: str) -> None:
        try:
            self._icon.notify(message, "HandControl")
        except Exception:  # notifications are best-effort
            log.debug("tray notification failed", exc_info=True)

    def run(self, ready: Callable[[], None]) -> None:
        """Block running the tray loop; ``ready`` is called once the icon is visible."""

        def setup(icon: pystray.Icon) -> None:
            icon.visible = True
            ready()

        self._icon.run(setup=setup)

    def stop(self) -> None:
        self._icon.stop()
```

- [x] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_tray.py -q`
Expected: `1 passed`.

- [x] **Step 5: Manually verify the tray**

Write this throwaway script to the scratchpad directory as `check_tray.py` (Write tool, not a heredoc):

```python
from handcontrol.tray import Tray


def ready():
    print("ready")
    tray.set_state("error", "test tooltip")


tray = Tray(
    on_enabled_changed=lambda enabled: print("enabled", enabled),
    on_preview_changed=lambda shown: print("preview", shown),
    on_quit=lambda: tray.stop(),
)
tray.run(ready=ready)
print("stopped")
```

Run: `uv run python <scratchpad>/check_tray.py`

Expected: a red disc with a hand glyph appears in the tray; hovering shows `HandControl - test tooltip`; right-click shows Enabled (checked), Show preview, Quit; toggling prints `enabled False` / `preview True`; Quit exits the process.

- [x] **Step 6: Commit**

```bash
git add handcontrol/tray.py tests/test_tray.py
git commit -m "feat: system tray icon and menu"
```

---

### Task 11: App lifecycle and CLI

**Files:**
- Create: `handcontrol/app.py`
- Modify: `handcontrol/__main__.py` (replace the placeholder entirely)
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: everything above. `App(settings: Settings, model_path: Path, *, preview: bool = False, use_tray: bool = True)` with `run()`, `quit()`, `start_pipeline()`, `stop_pipeline()`.
- Produces: `parse_args(argv) -> argparse.Namespace` with `preview`, `no_tray`, `camera`, `config`, `verbose`; `configure_logging(verbose: bool)`; `main(argv=None) -> int`.

- [x] **Step 1: Write the failing tests**

`tests/test_main.py`:

```python
from pathlib import Path

from handcontrol.__main__ import parse_args


def test_defaults():
    a = parse_args([])
    assert (a.preview, a.no_tray, a.camera, a.config, a.verbose) == (False, False, None, None, False)


def test_all_flags():
    a = parse_args(["--preview", "--no-tray", "--camera", "2", "--config", "c.toml", "-v"])
    assert a.preview and a.no_tray and a.verbose
    assert a.camera == 2
    assert a.config == Path("c.toml")
```

- [x] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_main.py -q`
Expected: FAIL with `ImportError: cannot import name 'parse_args'`.

- [x] **Step 3: Write `handcontrol/app.py`**

```python
"""Application lifecycle: tray on the main thread, gesture pipeline on a worker thread."""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from handcontrol.actions import ActionExecutor
from handcontrol.camera import Camera
from handcontrol.config import Settings
from handcontrol.gestures.base import GestureEngine
from handcontrol.gestures.start_menu import StartMenuSwipe
from handcontrol.gestures.two_finger_scroll import TwoFingerScroll
from handcontrol.hand import pose_from_raw
from handcontrol.model import ensure_model
from handcontrol.preview import Preview
from handcontrol.tracker import HandTracker
from handcontrol.tray import State, Tray

log = logging.getLogger(__name__)

CAMERA_RETRY_S = 3.0


class App:
    def __init__(self, settings: Settings, model_path: Path, *, preview: bool = False, use_tray: bool = True) -> None:
        self.settings = settings
        self.model_path = model_path
        self.preview_enabled = preview
        self._stop = threading.Event()
        self._quit = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_state: tuple[str, str] | None = None
        self.tray: Tray | None = None
        if use_tray:
            self.tray = Tray(
                on_enabled_changed=self._on_enabled_changed,
                on_preview_changed=self._on_preview_changed,
                on_quit=self.quit,
                preview=preview,
            )

    # ----- lifecycle -------------------------------------------------------

    def run(self) -> None:
        """Block until quit. With a tray, the pipeline starts once the icon is visible."""
        if self.tray is not None:
            self.tray.run(ready=self.start_pipeline)
        else:
            self.start_pipeline()
            while not self._quit.wait(0.2):
                pass
        self.stop_pipeline()

    def quit(self) -> None:
        self._quit.set()
        self.stop_pipeline()
        if self.tray is not None:
            self.tray.stop()

    def start_pipeline(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._pipeline, name="pipeline", daemon=True)
        self._thread.start()

    def stop_pipeline(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None

    # ----- tray callbacks --------------------------------------------------

    def _on_enabled_changed(self, enabled: bool) -> None:
        if enabled:
            self.start_pipeline()
        else:
            self.stop_pipeline()
            self._set_state("disabled", "disabled (webcam off)")

    def _on_preview_changed(self, enabled: bool) -> None:
        self.preview_enabled = enabled

    def _set_state(self, state: State, text: str) -> None:
        if (state, text) == self._last_state:
            return
        self._last_state = (state, text)
        log.info("state: %s (%s)", state, text)
        if self.tray is not None:
            self.tray.set_state(state, text)

    def _notify(self, message: str) -> None:
        log.info(message)
        if self.tray is not None:
            self.tray.notify(message)

    # ----- pipeline thread -------------------------------------------------

    def _pipeline(self) -> None:
        try:
            if not self.model_path.exists():
                self._set_state("running", "downloading hand model")
                self._notify("Downloading the hand model (8 MB), one time only.")
            ensure_model(self.model_path)
        except OSError as exc:
            log.error("%s", exc)
            self._set_state("error", "model download failed, see log")
            return
        try:
            self._loop()
        except Exception:
            log.exception("pipeline crashed")
            self._set_state("error", "pipeline crashed, see log")

    def _loop(self) -> None:
        s = self.settings
        camera = Camera(s.camera.index, s.camera.width, s.camera.height)
        tracker = HandTracker(self.model_path, s.tracker)
        engine = GestureEngine([TwoFingerScroll(s.scroll), StartMenuSwipe(s.start_menu)])
        from handcontrol import winput  # Windows-only module; imported here so tests never touch it

        executor = ActionExecutor(winput, wheel_step=s.scroll.wheel_step)
        preview = Preview()
        t0 = time.monotonic()
        try:
            while not self._stop.is_set():
                frame = camera.read()
                if frame is None:
                    engine.reset()
                    self._set_state("error", "camera unavailable, retrying")
                    self._stop.wait(CAMERA_RETRY_S)
                    continue
                self._set_state("running", "running")
                now = time.monotonic()
                try:
                    hands = tracker.detect(frame, int((now - t0) * 1000))
                except Exception:
                    log.exception("hand tracking failed on a frame")
                    continue
                raw = hands[0] if hands else None
                pose = pose_from_raw(raw, now, s.hand) if raw is not None else None
                for action in engine.update(pose, now):
                    log.debug("action: %s", action)
                    executor.execute(action)
                if self.preview_enabled:
                    preview.draw(frame, raw, pose, engine.states)
                elif preview.is_open:
                    preview.close()
        finally:
            preview.close()
            tracker.close()
            camera.release()
```

- [x] **Step 4: Replace `handcontrol/__main__.py`**

```python
"""Command-line entry point. Also used by the ``handcontrol-gui`` script under pythonw."""

from __future__ import annotations

import argparse
import logging
import logging.handlers
import os
import sys
from dataclasses import replace
from pathlib import Path

from handcontrol import __version__
from handcontrol.config import app_data_dir, load_settings


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="handcontrol", description="Control Windows with your hands.")
    parser.add_argument("--preview", action="store_true", help="show the debug preview window at start")
    parser.add_argument("--no-tray", action="store_true", help="run in the console without a tray icon (Ctrl+C quits)")
    parser.add_argument("--camera", type=int, default=None, metavar="N", help="camera index (overrides the config file)")
    parser.add_argument(
        "--config", type=Path, default=None, metavar="PATH",
        help="TOML config file (default: %%LOCALAPPDATA%%\\HandControl\\config.toml)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    parser.add_argument("--version", action="version", version=f"handcontrol {__version__}")
    return parser.parse_args(argv)


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    if sys.stdout is None or sys.stderr is None:  # pythonw: no console, log to a rotating file
        log_dir = app_data_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = logging.handlers.RotatingFileHandler(
            log_dir / "handcontrol.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
    else:
        handler = logging.StreamHandler(sys.stderr)
    logging.basicConfig(level=level, format=fmt, handlers=[handler])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(args.verbose)
    os.environ.setdefault("GLOG_minloglevel", "2")  # quieten MediaPipe native logging
    settings = load_settings(args.config)
    if args.camera is not None:
        settings = replace(settings, camera=replace(settings.camera, index=args.camera))

    from handcontrol.app import App  # heavy imports (mediapipe, cv2) after logging is configured

    app = App(
        settings,
        model_path=app_data_dir() / "models" / "hand_landmarker.task",
        preview=args.preview,
        use_tray=not args.no_tray,
    )
    try:
        app.run()
    except KeyboardInterrupt:
        app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [x] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest -q`
Expected: all tests pass (previous 43 + 6 actions + 3 model + 1 tray + 2 main = 55).

- [x] **Step 6: Run the app end to end in console mode**

Run: `uv run handcontrol --preview --no-tray -v`
Expected: the log shows the camera opening at 1280x720; a mirrored preview window appears with landmarks on your hand, finger flags like `th+ in+ mi+ ri+ pi+`, `facing=True` with your palm toward the camera, and `scroll: IDLE`, `start_menu: ARMED` when the palm is open. Raise the open hand quickly: the Start menu opens and the log shows `action: OpenStartMenu()`. Put the Start menu away, focus a scrollable window, hold index+middle together and move them: the log shows `action: Scroll(...)` and the window scrolls. Ctrl+C exits cleanly with no traceback.

- [x] **Step 7: Run the app in tray mode**

Run: `uv run handcontrol`
Expected: green tray icon with tooltip `HandControl - running`; Show preview opens and closes the preview window; unchecking Enabled turns the webcam LED off and the icon grey; re-checking turns it back on; Quit exits. Then simulate a missing camera with a wrong index: `uv run handcontrol --camera 9` gives a red icon with tooltip `camera unavailable, retrying`, and Quit still works.

- [x] **Step 8: Commit**

```bash
git add handcontrol/app.py handcontrol/__main__.py tests/test_main.py
git commit -m "feat: app lifecycle, pipeline thread and CLI"
```

---

### Task 12: Tune thresholds against real hands and document

**Files:**
- Modify: `handcontrol/config.py` (defaults only, if tuning changes them)
- Modify: `docs/superpowers/specs/2026-09-22-handcontrol-design.md` section 6 (keep in sync with any changed default)
- Modify: `README.md`

**Interfaces:** none new.

- [x] **Step 1: Confirm the palm-facing rule on real frames**

Already measured offline on MediaPipe's sample photos (victory.jpg and pointing_up.jpg are palms, thumbs_up.jpg is knuckles-forward): the rule in `palm_facing_camera()` was inverted from the first derivation and fixed, with the builder in `tests/handbuilder.py` flipped to match. Confirm live: run `uv run handcontrol --preview --no-tray -v`. Show the right hand, palm to camera: preview must read `facing=True`; turn the back of the hand to the camera: `facing=False`. Repeat with the left hand. If either hand is inverted, swap the `z < 0` / `z > 0` branches in the return line of `palm_facing_camera()`, flip `mirror = (handedness == "Right") == facing` in the builder to `!=`, update both docstrings, and rerun `uv run pytest -q`.

- [ ] **Step 2: Tune finger thresholds**

With the preview open, check: relaxed open hand shows `in+ mi+ ri+ pi+`; a fist shows all `-`; index+middle together shows `joined=True` and `two_finger=True`; the same two fingers in a V shows `joined=False`. Adjust `finger_extended_angle_deg` (lower if straight fingers read `-`, typical range 140-160) and `fingers_joined_max_m` (typical 0.025-0.04) in `HandSettings` until all four readings are reliable.

- [ ] **Step 3: Tune the swipe**

Raise the open palm at a natural speed ten times: it should fire every time and never fire while the hand is held still or drifts. Adjust `swipe_distance_palms` (1.0-2.0) and `swipe_window_s` (0.4-0.7) in `StartMenuSettings`.

- [ ] **Step 4: Tune scrolling**

In a browser, scroll a long page with the two-finger gesture. Adjust `gain_notches_per_palm` (3-8) so a comfortable hand movement scrolls about a screenful, `deadzone_palms` so a steady hand does not scroll, and `smoothing` (0.3-0.7) if motion feels jittery or laggy. Confirm the natural direction: fingers up moves the content up.

- [x] **Step 5: Write the changed defaults back**

Update the default values in `handcontrol/config.py` and the table in spec section 6 to the tuned numbers. `test_defaults_match_spec` in `tests/test_config.py` must be updated to the same numbers.

Run: `uv run pytest -q`
Expected: all tests pass.

- [ ] **Step 6: Run the manual acceptance checklist**

1. Tray icon appears; Enabled toggle turns the webcam LED on/off; Quit exits cleanly.
2. Open-palm upward swipe opens the Start menu; a second swipe closes it; waving sideways does nothing.
3. Two-finger up/down scrolls in Chrome, Explorer and Notepad with the natural direction; the scroll reaches the focused window even when the mouse pointer was elsewhere.
4. One minute of typing and ordinary hand movement produces no false triggers.
5. `uv run handcontrol-gui` starts without a console window and writes `%LOCALAPPDATA%\HandControl\handcontrol.log`.

Note any item that fails and fix it before moving on.

- [x] **Step 7: Write `README.md`**

```markdown
# HandControl

Control Windows with your hands. A system-tray app that watches your webcam
with Google MediaPipe hand tracking and turns two gestures into input.

| Gesture | What to do | What happens |
|---|---|---|
| Start menu | Hold one hand open, palm to the camera, and raise it quickly | Windows key: the Start menu opens (or closes) |
| Scroll | Extend index and middle finger together, other fingers curled, and move them up or down | The focused app scrolls in the natural direction: fingers up, content moves up |

## Requirements

Windows 10/11, a webcam, [Python 3.13](https://www.python.org/downloads/) and [uv](https://docs.astral.sh/uv/).

## Run

```
uv sync
uv run handcontrol --preview      # console, plus a debug window showing what the camera sees
uv run handcontrol                # tray icon only
uv run handcontrol-gui            # no console window; logs go to %LOCALAPPDATA%\HandControl\handcontrol.log
```

The first run downloads the 8 MB hand model to `%LOCALAPPDATA%\HandControl\models\`.

Tray menu: **Enabled** (unchecking releases the webcam), **Show preview**, **Quit**.
Icon colour: green running, grey disabled, red error (hover for the reason).

Flags: `--camera N` picks another webcam, `--config PATH` uses another config file, `-v` logs every action.

## Configure

Create `%LOCALAPPDATA%\HandControl\config.toml` with any subset of these keys (defaults shown):

```toml
[camera]
index = 0
width = 1280
height = 720

[hand]
finger_extended_angle_deg = 150   # straighter than this = extended
fingers_joined_max_m = 0.03       # index/middle tips closer than this = joined

[start_menu]
swipe_distance_palms = 1.5        # rise needed, in palm heights
swipe_window_s = 0.5              # ... within this many seconds
swipe_cooldown_s = 1.5

[scroll]
engage_frames = 3                 # frames the pose must hold before scrolling starts
release_frames = 5                # frames the pose may vanish before scrolling stops
deadzone_palms = 0.02             # ignore slower movement (palm heights per frame)
gain_notches_per_palm = 4.0       # wheel notches per palm height of movement
smoothing = 0.5                   # 0 = raw, closer to 1 = smoother but laggier
wheel_step = 120                  # wheel units per notch; 120 is one standard click
```

Use `--preview` to see finger flags, palm facing, and gesture states while tuning.

## Develop

```
uv run pytest
```

Design: `docs/superpowers/specs/2026-09-22-handcontrol-design.md`.
```

If Step 5 changed any default, put the tuned numbers in this table too.

- [ ] **Step 8: Commit**

```bash
git add README.md handcontrol/config.py tests/test_config.py docs/superpowers/specs/2026-09-22-handcontrol-design.md
git commit -m "docs: README, tuned gesture defaults"
```

---

## Self-review notes

- Spec coverage: §1 gestures → Tasks 5, 6; §2 stack → Task 1; §3.1 layout → file table (plus `model.py`, agreed in the spec edit); §3.2 types → Task 3/4; §3.3 geometry → Task 3; §3.4 gestures/engine → Tasks 4-6; §3.5 actions → Task 7; §3.6 tray/app/config/entry points → Tasks 2, 10, 11; §3.7 loop → Task 11; §4 error handling → Tasks 8 (camera, model), 11 (inference, crash), 2 (config); §5 unit tests → Tasks 2-7, 8, 10, 11; §5 manual acceptance → Task 12; §6 defaults → Task 2 and Task 12; §7 assumptions honoured (thumb clarification recorded in the spec).
- Names are consistent across tasks: `pose_from_raw`, `HandPose.is_open_palm/is_two_finger/two_finger_point/palm_center/palm_size`, `GestureEngine.update/reset/states`, `StartMenuSwipe`, `TwoFingerScroll`, `ActionExecutor(backend, wheel_step)`, `Camera.read/release`, `HandTracker.detect/close`, `ensure_model(path, fetch)`, `Preview.draw/close/is_open`, `Tray.run(ready)/stop/set_state/notify`, `App.run/quit/start_pipeline/stop_pipeline`.
