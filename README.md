# HandControl

Control Windows with your hands. A system-tray app that watches your webcam
with Google MediaPipe hand tracking and turns hand gestures into input.

| Gesture | What to do | What happens |
|---|---|---|
| Clap sign | Bring both open hands together (any orientation) and hold for a moment | Windows key: the Start menu opens (or closes) |
| Rock-on | Index and pinky up, middle and ring curled, hold ~0.6 s | Opens YouTube in your default browser |
| Volume | One open hand, fingers pointing up = louder, pointing down = quieter; keeps going while held | Media volume keys, 2% per step |
| Middle finger | Middle finger up, others curled, hold ~0.6 s | Win+D: shows the desktop (again brings the windows back) |
| Scroll | Extend index and middle finger together, other fingers curled, and move them up or down | The focused app scrolls in the natural direction: fingers up, content moves up |

Held gestures fire once; let go before making them again. Tip for the clap:
the camera has to see both hands, so fingers toward the screen or a small gap
between the palms works better than palms pressed flat together.

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

Create `%LOCALAPPDATA%\HandControl\config.toml` with any subset of these keys (defaults shown).
Frame counts are at roughly 30 frames per second; distances are in hand widths
(index knuckle to pinky knuckle), so they work at any distance from the camera.

```toml
[camera]
index = 0
width = 1280
height = 720

[hand]
finger_extended_angle_deg = 150   # straighter than this = extended
fingers_joined_max_m = 0.03       # index/middle tips closer than this = joined
vertical_max_deg = 35             # within this angle of straight up/down = pointing up/down
min_direction_len = 0.6           # shorter wrist-to-knuckle length = fingers toward the camera, ignored

[start_menu]                      # clap sign
max_distance_widths = 1.2         # how close the two palm centres must be
hold_frames = 8
cooldown_s = 1.5

[youtube]                         # rock-on
hold_frames = 18
cooldown_s = 2.0
url = "https://www.youtube.com"

[show_desktop]                    # middle finger
hold_frames = 18
cooldown_s = 1.5

[volume]                          # open hand pointing up or down
engage_frames = 10                # frames before the first step
repeat_frames = 5                 # frames between steps while held

[scroll]
engage_frames = 3                 # frames the pose must hold before scrolling starts
release_frames = 5                # frames the pose may vanish before scrolling stops
deadzone_widths = 0.02            # ignore slower movement (hand widths per frame)
gain_notches_per_width = 3.0      # wheel notches per hand width of movement
smoothing = 0.5                   # 0 = raw, closer to 1 = smoother but laggier
wheel_step = 120                  # wheel units per notch; 120 is one standard click
```

Use `--preview` to see finger flags, pointing direction and gesture states while tuning.

## Develop

```
uv run pytest
```

Design: `docs/superpowers/specs/2026-09-22-handcontrol-design.md`.
Plans: `docs/superpowers/plans/`.
