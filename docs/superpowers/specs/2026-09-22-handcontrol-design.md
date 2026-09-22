# HandControl — Design

Date: 2026-09-22
Status: v1.1 approved 2026-09-22 (stack: Python). v1.0 shipped an open-palm upward
swipe for the Start menu; v1.1 replaces it with the gesture set below.

## 1. Goal

A Windows system-tray app that watches the webcam and turns hand gestures into
Windows input. Version 1.1 ships five gestures:

| Gesture | Pose | Fires | Effect |
|---|---|---|---|
| Bomb | A fist held 6 frames (~0.2 s), then opened into a flat hand within 12 frames (~0.4 s), any orientation | On reaching the open hand | Windows key (toggles the Start menu) |
| Rock-on | Index + pinky extended, middle + ring curled | Held 18 frames (~0.6 s) | Opens YouTube in the default browser |
| Volume | One open hand pointing up = louder, pointing down = quieter | After 10 frames, then one step every 5 frames while held | Media volume keys, 2% per step |
| Middle finger | Middle extended, index/ring/pinky curled | Held 18 frames | Win+D: show desktop (again restores the windows) |
| Two-finger scroll | Index and middle extended and touching, ring and pinky curled, moved up or down | While held | Mouse-wheel scroll in the focused app, natural direction (fingers up → content moves up) |

Held gestures must be released before they can fire again, and have a cooldown.
The bomb replaced a two-hand clap sign (v1.1 first draft): palms brought
together are edge-on to the camera and MediaPipe rarely sees both hands.

Non-goals for v1.1: start-with-Windows, packaged `.exe`, settings window,
GPU inference, click/cursor control, telling palm-up from palm-down.

## 2. Stack

- Python 3.13, project managed with `uv` (`pyproject.toml`, lock file).
- `mediapipe` 1.0.1 — Tasks API `HandLandmarker`, `VIDEO` running mode (synchronous), CPU, `num_hands = 2`.
- `opencv-python` — webcam capture and the optional preview window.
- `pystray` + `Pillow` — tray icon and menu.
- `ctypes` (stdlib) — `SendInput` for key taps/chords and wheel events; `GetForegroundWindow`, `GetCursorPos`, `SetCursorPos`. `webbrowser` (stdlib) for URLs.
- `tomllib` (stdlib) — optional config file.
- `pytest` — unit tests.

Verified on this machine on 2026-09-22: the mediapipe 1.0.1 wheel installs and
imports on Python 3.13.8; the Logitech StreamCam opens via `CAP_DSHOW` (always
1920×1080 whatever is requested, 60 fps capture, ~3.5 s to open);
`detect_for_video` takes 17.7 ms per 1080p frame on CPU for one hand
(resolution barely matters: 14.1 ms at 640×360). A second visible hand adds
roughly the landmark-model cost again.

Alternatives considered: Electron + MediaPipe JS (native input module, 200 MB
app) and C#/.NET (no official bindings). Rejected.

## 3. Architecture

Two threads:

- **Main thread** runs the pystray message loop.
- **Pipeline thread** runs a ~30 Hz loop: capture → track (up to two hands) → poses → scene → gestures → actions → (preview). The preview is drawn from this thread because OpenCV HighGUI must be driven from one thread.

### 3.1 Package layout

```
handcontrol/
  __main__.py            CLI: --preview, --no-tray, --camera N, --config PATH, -v; file log under pythonw
  app.py                 App: lifecycle, tray callbacks, pipeline thread, builds the gesture list
  tray.py                pystray icon + menu (Enabled, Show preview, Quit); icon colour = state
  camera.py              Camera: lazy open, self-healing read, release
  tracker.py             HandTracker: HandLandmarker VIDEO mode → list[RawHand]
  model.py               ensure_model(): download hand_landmarker.task if missing
  hand.py                RawHand, HandPose (pure geometry), Scene (0-2 poses)
  gestures/
    base.py              Gesture protocol + GestureEngine (priority + mutual exclusion)
    poses.py             scene predicates: clap(), rock_on, middle_finger, volume_up, volume_down
    hold.py              HoldGesture: predicate held N frames → one action, release + cooldown
    repeat.py            RepeatGesture: predicate held → action on engage, then every N frames
    two_finger_scroll.py TwoFingerScroll state machine + wheel-notch accumulator
  actions.py             TapKeys, Scroll, OpenUrl; InputBackend protocol; ActionExecutor
  winput.py              ctypes user32 wrappers + webbrowser open_url
  config.py              Settings dataclasses with defaults; optional TOML override
  preview.py             debug overlay: landmarks of every hand, flags, pointing, gesture states
tests/
  handbuilder.py         build_hand(): synthetic RawHand for any finger combination and direction
  test_*.py              one per pure module
```

`hand.py`, `gestures/*`, `config.py` and the action types are pure: no threads,
no I/O, no MediaPipe import. They carry all the logic and all the tests.

### 3.2 Data types

```python
RawHand(landmarks: list[Point3], world: list[Point3], handedness: str, score: float)

HandPose(
    fingers: Mapping[Finger, bool],   # THUMB..PINKY -> extended?
    hand_width: float,                # image-space index MCP <-> pinky MCP; the unit for all motion thresholds
    palm_center: Point2,              # image space
    two_finger_point: Point2,         # midpoint of index & middle tips
    two_fingers_joined: bool,         # world distance index tip <-> middle tip <= fingers_joined_max_m
    direction_deg: float,             # image-space wrist -> middle MCP: 0 up, 90 right, 180 down, -90 left
    direction_len: float,             # |wrist -> middle MCP| / hand_width; small = fingers toward the camera
    pointing: "up" | "down" | None,   # direction within vertical_max_deg of up/down AND direction_len >= min_direction_len
    t: float,
)
    is_open_hand      index, middle, ring, pinky extended (thumb ignored)
    is_two_finger     index + middle extended and joined, ring + pinky curled
    is_rock_on        index + pinky extended, middle + ring curled
    is_middle_finger  middle extended, index + ring + pinky curled

Scene(hands: tuple[HandPose, ...], t: float)   # sorted by hand_width, largest first
    primary   hands[0] or None
    single    hands[0] only when exactly one hand is visible, else None
    pair      (hands[0], hands[1]) when two are visible, else None

Action = TapKeys(vks: tuple[int, ...]) | Scroll(notches: int) | OpenUrl(url: str)
```

### 3.3 Hand geometry (`hand.py`)

- **Finger extended**: angle at the bending joint (MCP→PIP→TIP; thumb CMC→MCP→TIP) from world landmarks ≥ `finger_extended_angle_deg` (150°). Orientation- and distance-invariant.
- **Fingers joined**: world distance index tip ↔ middle tip ≤ `fingers_joined_max_m` (0.03 m).
- **Hand width** (image-space index MCP ↔ pinky MCP) is the unit for every motion threshold. Unlike wrist→knuckle length it does not collapse when the fingers point at the camera.
- **Pointing**: `direction_deg` is measured from the image-space wrist→middle-MCP vector; `pointing` is "up"/"down" only when that vector is within `vertical_max_deg` (35°) of vertical and at least `min_direction_len` (0.6) hand-widths long, so a foreshortened hand is neither.
- Palm-facing-camera detection was removed in v1.1: it depends on the handedness label whose convention proved orientation-dependent, and no gesture needs it.

### 3.4 Gestures

`Gesture` protocol: `update(scene: Scene, t: float) -> list[Action]`, `engaged: bool`, `state: str`, `reset()`.

`GestureEngine` runs gestures in priority order. If one is `engaged`, every other gesture is `reset()` and skipped for that frame. Order: bomb, scroll, rock-on, middle finger, volume up, volume down.

**Which hand a gesture looks at**

- Bomb, scroll, rock-on and middle finger use `scene.primary` (the larger hand), so a resting second hand does not block them.
- Volume uses `scene.single`, so a second visible hand never changes the volume by accident.

**TransitionGesture(name, start, end, action, min_start_frames, max_transition_frames, cooldown_s)** (the bomb)

- `IDLE` counts consecutive frames of the start pose (fist); after `min_start_frames` → `ARMED`.
- `ARMED`: the end pose (open hand) fires `action` and enters `RELEASE`; the start pose keeps it armed; any other pose is tolerated for up to `max_transition_frames` consecutive frames (the fingers in motion), after which it drops to `IDLE`.
- `RELEASE` lasts while the end pose is held, so the freshly opened hand cannot start the volume gesture; then `COOLDOWN` until `cooldown_s` after the fire, then `IDLE`. A new bomb needs a new fist.
- `engaged` while `ARMED` or `RELEASE`.

**HoldGesture(name, predicate, action, hold_frames, cooldown_s)**

- `IDLE` → `HOLDING` while the predicate is true; a false frame drops back to `IDLE` (count restarts).
- After `hold_frames` consecutive true frames: emit `action`, enter `RELEASE`.
- `RELEASE` waits for a false frame (the pose must be let go), then `COOLDOWN` until `cooldown_s` after firing, then `IDLE`.
- `engaged` while `HOLDING` or `RELEASE`.

**RepeatGesture(name, predicate, action, engage_frames, repeat_frames)**

- `IDLE` → `ACTIVE` after `engage_frames` consecutive true frames; emits `action` on entering `ACTIVE` and again every `repeat_frames` frames while the predicate stays true. A false frame → `IDLE`.
- `engaged` while `ACTIVE`.

**Predicates (`gestures/poses.py`)**

- `fist`, `open_hand`, `rock_on`, `middle_finger`: `scene.primary` matches the pose (`is_fist` = index to pinky all curled, thumb ignored).
- `volume_up` / `volume_down`: `scene.single` is an open hand with `pointing` "up" / "down".

**TwoFingerScroll** (unchanged logic, now on `scene.primary` and in hand-width units): engage after `engage_frames` (3) of the two-finger pose; per frame `dy = Δy / hand_width`, EMA smoothing, dead zone, `notches_acc += dy × gain_notches_per_width` (3.0), emit whole notches, keep the remainder; tolerate `release_frames` (5) of pose loss. Fingers down → positive notches → content moves down (natural direction).

### 3.5 Actions (`actions.py`, `winput.py`)

- `TapKeys(vks)` → one `SendInput` call: key-down for each key in order, key-up in reverse. Constants: `OPEN_START_MENU = TapKeys((VK_LWIN,))`, `SHOW_DESKTOP = TapKeys((VK_LWIN, VK_D))`, `VOLUME_UP = TapKeys((VK_VOLUME_UP,))`, `VOLUME_DOWN = TapKeys((VK_VOLUME_DOWN,))`.
- `Scroll(n)` → park the cursor inside the foreground window if it is elsewhere (Windows routes wheel events to the window under the cursor), then `MOUSEEVENTF_WHEEL` with `n × wheel_step`.
- `OpenUrl(url)` → `webbrowser.open(url)` (default browser, new tab).
- `SendInput` returning fewer events than sent is logged, never raised.

### 3.6 Tray, lifecycle, config

Unchanged from v1.0: menu Enabled / Show preview / Quit; Disabled releases the
webcam; icon green/grey/red with a tooltip; model downloaded on first run to
`%LOCALAPPDATA%\HandControl\models\`; config at `%LOCALAPPDATA%\HandControl\config.toml`;
`handcontrol` (console) and `handcontrol-gui` (pythonw, rotating file log) entry points.

### 3.7 Pipeline loop

```
while running:
    frame = camera.read()
    if frame is None: engine.reset(); tray.error("camera unavailable"); wait 3 s; continue
    raws = tracker.detect(frame, t_ms)                     # 0..2 hands
    scene = Scene(sorted(pose_from_raw(r, t, hand_settings) for r in raws, by hand_width desc), t)
    for action in engine.update(scene, t): executor.execute(action)
    if preview_enabled: preview.draw(frame, raws, scene, engine.states)
```

## 4. Error handling

| Failure | Behaviour |
|---|---|
| No camera / camera unplugged | Red icon + tooltip; retry every 3 s; gestures reset |
| Model file missing | Download on first run with a tray notification; failure → red icon |
| Inference raises | Log, skip the frame |
| `SendInput` short count | Log warning |
| Browser cannot be opened | Log warning |
| Hand lost mid-gesture | Hold/repeat gestures drop to IDLE; scroll tolerates 5 frames |
| Config file malformed | Log, run with defaults |

## 5. Testing

Unit tests (`pytest`, no camera, no MediaPipe): hand geometry and pose flags for
every gesture pose in four directions (up, down, toward camera, sideways);
`Scene` ordering and `primary`/`single`/`pair`; each predicate including the
two-hand distance rule and the single-hand rule for volume; `HoldGesture`
(fires once, restart on drop-out, release required, cooldown); `RepeatGesture`
(engage, cadence, release); scroll direction, accumulator, dead zone, flicker
tolerance; engine mutual exclusion; executor mapping for every action; config
defaults and overrides.

Manual acceptance with `handcontrol --preview`: each of the five gestures works
from a natural position; a resting second hand does not block scroll; two hands
approaching for a clap do not change the volume; one minute of typing and
ordinary movement causes no false trigger; `handcontrol-gui` runs silently.

## 6. Default settings

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
vertical_max_deg = 35
min_direction_len = 0.6

[start_menu]                # bomb: fist, then open hand
fist_frames = 6
open_within_frames = 12
cooldown_s = 1.5

[youtube]                   # rock-on
hold_frames = 18
cooldown_s = 2.0
url = "https://www.youtube.com"

[show_desktop]              # middle finger
hold_frames = 18
cooldown_s = 1.5

[volume]                    # open hand pointing up / down
engage_frames = 10
repeat_frames = 5

[scroll]
engage_frames = 3
release_frames = 5
deadzone_widths = 0.02
gain_notches_per_width = 3.0
smoothing = 0.5
wheel_step = 120
```

## 7. Decisions taken on assumptions (override any of these)

1. The bomb and the volume gesture share the open hand: after a bomb the hand must be closed or lowered before volume can engage, and raising a closed hand then opening it reads as a bomb rather than the start of a volume change. Both timings are settings.
2. Palm-up is not distinguished from palm-down anywhere.
3. Volume repeats while held, like holding a keyboard volume key.
4. "Reduce all windows" is Win+D (show desktop), so the same gesture brings the windows back.
5. Rock-on opens a new YouTube tab each time; the hold-and-release rule and a 2 s cooldown prevent bursts.
6. Either hand works for single-hand gestures; the larger hand in view is used, except volume which needs exactly one hand visible.
7. Startup-with-Windows and a packaged `.exe` are deferred.
