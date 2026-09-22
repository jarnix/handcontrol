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
Implementation plan: `docs/superpowers/plans/2026-09-22-handcontrol.md`.
