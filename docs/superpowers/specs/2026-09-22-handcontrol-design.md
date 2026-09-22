# HandControl — Design

Date: 2026-09-22
Status: approved 2026-09-22 (stack: Python)

## 1. Goal

A Windows system-tray app that watches the webcam and turns hand gestures into
Windows input. Version 1 ships exactly two gestures:

| Gesture | Trigger | Effect |
|---|---|---|
| Start menu | One open hand, palm facing the camera, swept upward | Press the Windows key (toggles the Start menu) |
| Two-finger scroll | Index and middle finger extended and touching, other fingers curled, moved up or down | Mouse-wheel scroll in the focused app, "natural" direction (fingers up → content moves up → wheel scrolls down) |

Non-goals for v1: start-with-Windows, packaged `.exe`, settings window,
additional gestures, two-hand gestures, GPU inference, click/cursor control.

## 2. Stack

- Python 3.13, project managed with `uv` (`pyproject.toml`, lock file).
- `mediapipe` 1.0.1 — Tasks API `HandLandmarker`, `VIDEO` running mode (synchronous), CPU.
- `opencv-python` — webcam capture and the optional preview window.
- `pystray` + `Pillow` — tray icon and menu.
- `ctypes` (stdlib) — `SendInput` for the Windows key and wheel events; `GetForegroundWindow`, `GetCursorPos`, `SetCursorPos`. No third-party input library.
- `tomllib` (stdlib) — optional config file.
- `pytest` — unit tests.

Verified on this machine on 2026-09-22 in a throwaway venv: the mediapipe 1.0.1
wheel installs and imports on Python 3.13.8; the Logitech StreamCam opens via
`CAP_DSHOW` at 1920×1080 in 2.3 s; `detect_for_video` averages 19 ms per
1080p frame on CPU.

Alternatives considered:

- Electron + MediaPipe JS (WASM/WebGL). GPU inference and easy webcam access, but input injection needs a native Node module built against the Electron ABI, and the app is ~200 MB. More moving parts for no v1 benefit.
- C#/.NET tray app. No official MediaPipe bindings; .NET is not installed here. Rejected.

## 3. Architecture

Two threads:

- **Main thread** runs the pystray message loop (`icon.run()`).
- **Pipeline thread** runs a ~30 Hz loop: capture → track → pose → gestures → actions → (preview). The preview window is drawn from this same thread because OpenCV HighGUI must be driven from one thread.

There is no separate capture thread: `VideoCapture.read()` blocks for one frame
period and paces the loop, and synchronous inference at 10–20 ms fits inside it.

### 3.1 Package layout

```
handcontrol/
  __main__.py            entry point: CLI args → App
  app.py                 App: owns Settings, Tray, pipeline thread; start/stop/pause; model download
  tray.py                pystray icon + menu (Enabled, Show preview, Quit); icon colour = state
  camera.py              Camera: open/read/release with reconnect backoff
  tracker.py             HandTracker: wraps HandLandmarker → list[RawHand]
  hand.py                HandPose: pure geometry from RawHand (finger flags, palm facing, palm size, key points)
  gestures/
    base.py              Gesture protocol + GestureEngine (priority + mutual exclusion)
    start_menu.py        StartMenuSwipe state machine
    two_finger_scroll.py TwoFingerScroll state machine + wheel-notch accumulator
  actions.py             Action types (OpenStartMenu, Scroll) + ActionExecutor
  winput.py              thin ctypes wrappers over user32 (SendInput, foreground window, cursor)
  config.py              Settings dataclass with defaults; optional TOML override
  preview.py             debug overlay: landmarks, finger flags, gesture states, fps
tests/
  fixtures/              synthetic landmark sets (open palm, two-finger, fist)
  test_hand.py
  test_gestures.py
  test_config.py
docs/superpowers/specs/  this document
```

`hand.py`, `gestures/*`, `actions.py` (types) and `config.py` are pure: no
threads, no I/O, no MediaPipe import. They carry all the logic and all the
tests. `camera.py`, `tracker.py`, `winput.py`, `tray.py`, `preview.py` are thin
adapters tested manually through the preview window.

### 3.2 Data types

```python
RawHand(landmarks: list[Point3], world: list[Point3], handedness: str, score: float)
    # 21 image landmarks, normalized 0..1 (y grows downward), z relative depth
    # 21 world landmarks in metres, origin at the hand centre

HandPose(
    fingers: dict[Finger, bool],      # THUMB..PINKY -> extended?
    palm_facing_camera: bool,
    palm_size: float,                 # image-space distance wrist -> middle MCP
    palm_center: (x, y),              # image space
    two_finger_point: (x, y),         # midpoint of index & middle tips, image space
    two_fingers_joined: bool,         # index tip <-> middle tip within a few cm (world space)
    t: float,                         # monotonic seconds
)

Action = OpenStartMenu() | Scroll(notches: int)
```

### 3.3 Hand geometry (`hand.py`)

- **Finger extended**: angle at the PIP joint (MCP→PIP→TIP) computed from world landmarks is ≥ `finger_extended_angle_deg` (default 150°). Thumb uses MCP→IP→TIP. World landmarks make this independent of camera angle and distance.
- **Fingers joined**: world distance between index tip and middle tip ≤ `fingers_joined_max_m` (default 0.03 m).
- **Palm facing camera**: sign of the z-component of `(index_mcp − wrist) × (pinky_mcp − wrist)` on image landmarks, combined with handedness. The sign convention is fixed during implementation by checking real frames in the preview window, and the rule is written down in a code comment.
- **Palm size** is the normalizer: all motion thresholds are expressed in "palm units" so the same physical movement gives the same result at any distance from the camera.
- **Open palm** = all five fingers extended and palm facing camera.
- **Two-finger pose** = index and middle extended and joined; ring and pinky curled; thumb ignored.

### 3.4 Gestures

`Gesture` protocol: `update(pose: HandPose | None, t: float) -> list[Action]`,
`engaged: bool`, `state: str`, `reset()`.

`GestureEngine` holds gestures in priority order `[TwoFingerScroll, StartMenuSwipe]`.
Each frame it passes the pose to every gesture. If one gesture is `engaged`, every
other gesture is `reset()` and receives `None` for that frame, so a scroll in
progress can never fire the Start menu and vice versa. Only one hand is tracked
(`num_hands = 1`), so "which hand" never has to be arbitrated.

**StartMenuSwipe**

- `IDLE` → `ARMED` when an open palm is seen. While `ARMED`, keep a deque of `(t, y)` samples of the palm centre over the last `swipe_window_s` (0.5 s).
- Fire when `max(y in window) − y_now ≥ swipe_distance_palms × palm_size` (default 1.5 palms), i.e. the hand rose by 1.5 palm heights within half a second. Emit `OpenStartMenu`, enter `COOLDOWN` for `swipe_cooldown_s` (1.5 s).
- Any frame without an open palm → `IDLE` (deque cleared). Cooldown ends → `IDLE`.
- `engaged` is true only while `ARMED`. The scroll pose is not an open palm, so a resting open hand never blocks scrolling for long.

**TwoFingerScroll**

- `IDLE` → `TRACKING` after the two-finger pose has been held for `scroll_engage_frames` (3) consecutive frames. Entering `TRACKING` records the previous `two_finger_point`.
- Each `TRACKING` frame: `dy = (y_now − y_prev) / palm_size` (positive = fingers moved down in the image). Apply EMA smoothing (`scroll_smoothing` 0.5) and a dead zone (`scroll_deadzone_palms` 0.02). `notches_acc += dy × scroll_gain` (default 4 notches per palm height). Whenever `|notches_acc| ≥ 1`, emit `Scroll(int(notches_acc))` and keep the remainder. Sign: fingers down → positive notches → content moves down, which is wheel "up" in Windows terms. Fingers up → negative → wheel down. This is the natural / Apple direction.
- Pose lost for up to `scroll_release_frames` (5 frames ≈ 170 ms) is tolerated (landmark flicker); longer → `IDLE`, accumulator cleared.
- `engaged` is true while `TRACKING`.

### 3.5 Actions (`actions.py`, `winput.py`)

- `OpenStartMenu` → `SendInput` key down + key up for `VK_LWIN`.
- `Scroll(n)` → first ensure the cursor is over the foreground window: if `GetCursorPos()` is outside `GetWindowRect(GetForegroundWindow())`, `SetCursorPos` to the window centre. Then `SendInput` `MOUSEEVENTF_WHEEL` with `mouseData = n × wheel_step` (default 120, one notch). Windows delivers the wheel to the window under the cursor, so this is what makes "the focused app" receive it.
- `SendInput` returning 0 is logged as a warning, never raised.

### 3.6 Tray (`tray.py`) and app lifecycle (`app.py`)

Menu: **Enabled** (checkbox), **Show preview** (checkbox), **Quit**.

- Disabled = pipeline thread stopped and camera released (webcam LED off). Enabled = pipeline started.
- Icon is drawn with Pillow: a simple hand glyph on a coloured disc. Green = running, grey = disabled, red = error. Tooltip carries the state text ("HandControl — running", "Camera unavailable", …).
- On start, `App` resolves the model at `%LOCALAPPDATA%\HandControl\models\hand_landmarker.task` and downloads it from the official Google storage URL if missing (tray notification "Downloading model…"). Failure → red icon, Quit still works.
- Config is read from `%LOCALAPPDATA%\HandControl\config.toml` if present; only listed keys override defaults. `--config PATH` overrides the location.
- Entry points: `handcontrol` (console script; logs to stdout; flags `--preview`, `--no-tray`, `--camera N`, `--config PATH`, `-v`) and `handcontrol-gui` (GUI script that runs under `pythonw`, no console; logs to `%LOCALAPPDATA%\HandControl\handcontrol.log`, rotating).

### 3.7 Pipeline loop (pipeline thread)

```
while running:
    frame = camera.read()                      # BGR, 1280x720
    if frame is None:
        tracker.reset(); engine.reset(); tray.error("Camera unavailable"); camera.reconnect(); continue
    raw = tracker.detect(frame, t_ms)          # 0 or 1 hands
    pose = HandPose.from_raw(raw[0], t) if raw else None
    for action in engine.update(pose, t):
        executor.execute(action)
    if preview_enabled:
        preview.draw(frame, pose, engine); cv2.waitKey(1)
```

Camera default 1280×720 (MediaPipe resizes internally; this keeps colour
conversion cheap and startup fast). Camera frames are processed un-mirrored;
only the preview is flipped for display. Timestamps are monotonic milliseconds
and strictly increasing, as `VIDEO` mode requires.

## 4. Error handling

| Failure | Behaviour |
|---|---|
| No camera / camera unplugged | Red icon + tooltip; retry every 3 s; no crash; gestures reset |
| Model file missing | Download on first run with a tray notification; failure → red icon with message |
| Inference raises | Log, skip the frame, keep running |
| `SendInput` fails | Log warning |
| Hand lost mid-gesture | Gesture resets after the tolerance window; no stray actions |
| Config file malformed | Log the TOML error, run with defaults |

## 5. Testing

Unit tests (`pytest`, no camera, no MediaPipe import):

- `test_hand.py`: synthetic landmark fixtures for open palm, two-finger, fist, and a "victory" (spread) pose → expected finger flags, joined flag, palm facing flag, palm size.
- `test_gestures.py`: scripted `(pose, t)` sequences →
  - fast upward open-palm sweep fires exactly once, then cooldown suppresses a second one;
  - slow upward drift over 2 s does not fire;
  - open palm moving sideways or downward does not fire;
  - two-finger pose held then moved up by N palms emits negative notches with the expected total; moved down emits positive;
  - movement below the dead zone emits nothing;
  - one-frame landmark flicker during scroll does not drop `TRACKING`;
  - accumulator carries the fractional remainder across frames;
  - engine: while scroll is engaged, an open-palm sweep does not fire.
- `test_config.py`: defaults; partial TOML override; malformed TOML falls back.

Manual acceptance (with `handcontrol --preview`):

1. Tray icon appears; Enabled toggle turns the webcam LED on/off; Quit exits cleanly.
2. Open-palm upward swipe opens the Start menu; a second swipe closes it; waving sideways does nothing.
3. Two-finger up/down scrolls in Chrome, Explorer and Notepad with the natural direction; scroll goes to the focused window even if the mouse was elsewhere.
4. Typing and normal hand movement for a minute cause no false triggers.
5. Thresholds are tuned from the preview readout and written back as the defaults.

## 6. Default settings (starting values, tuned during implementation)

```toml
[camera]
index = 0
width = 1280
height = 720

[tracker]
min_hand_detection_confidence = 0.5
min_hand_presence_confidence = 0.5
min_tracking_confidence = 0.5

[hand]
finger_extended_angle_deg = 150
fingers_joined_max_m = 0.03

[start_menu]
swipe_distance_palms = 1.5
swipe_window_s = 0.5
swipe_cooldown_s = 1.5

[scroll]
engage_frames = 3
release_frames = 5
deadzone_palms = 0.02
gain_notches_per_palm = 4.0
smoothing = 0.5
wheel_step = 120
```

## 7. Decisions taken on assumptions (override any of these)

1. Python over Electron, for the reasons in section 2.
2. "Palm up" is read as the palm facing the camera with the hand held upright, not the palm facing the ceiling. A ceiling-facing palm is foreshortened and unreliable from a desk webcam.
3. The Start-menu gesture presses the Windows key, so it toggles the menu rather than only opening it.
4. Scroll targets the focused window; if the cursor is not over it, the cursor is moved to its centre first.
5. Either hand works; only one hand is tracked at a time.
6. "Disabled" in the tray fully releases the webcam.
7. Startup-with-Windows and a packaged `.exe` are deferred; the app is run with `uv run handcontrol-gui` or a shortcut to it.
