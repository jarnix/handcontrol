# HandControl v1.1 Gestures Implementation Plan

> **Update (2026-09-22, after live testing):** the clap sign was replaced by a "bomb" (fist held ~0.2 s, then opened into a flat hand) implemented as a generic `TransitionGesture` in `handcontrol/gestures/transition.py`; `clap()` and its settings are gone. The spec is the source of truth for the current gesture set.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the open-palm swipe with four new gestures (clap sign → Start menu, rock-on → YouTube, open hand up/down → volume, middle finger → show desktop) on top of the existing two-finger scroll, using generic hold/repeat gesture classes.

**Architecture:** Gestures now consume a `Scene` of up to two `HandPose`s. Two generic classes (`HoldGesture`, `RepeatGesture`) plus scene predicates replace bespoke state machines. Actions generalise to `TapKeys`, `Scroll`, `OpenUrl`. Palm-facing detection and the swipe gesture are removed. Hand width becomes the single motion unit.

**Tech Stack:** unchanged (Python 3.13, uv, mediapipe 1.0.1, opencv-python, pystray, ctypes, pytest).

**Spec:** `docs/superpowers/specs/2026-09-22-handcontrol-design.md` (v1.1). This plan continues on branch `feature/handcontrol-v1`; the v1.0 plan is `2026-09-22-handcontrol.md`.

## Global Constraints

- Same as the v1.0 plan: pure modules never import cv2/mediapipe/pystray/ctypes; tests need no camera; every threshold comes from `Settings` with the defaults of spec §6; `uv run pytest -q` green at the end of every task; commit per task with a plain message (no attribution trailers); create files with the Write tool (the Bash tool breaks on apostrophes).
- Motion unit is `HandPose.hand_width` everywhere. `palm_size` is removed.
- `Gesture.update(scene, t)`; nothing receives a bare pose any more.

---

### Task 1: Actions and input backend

**Files:** modify `handcontrol/actions.py`, `handcontrol/winput.py`; test `tests/test_actions.py`.

**Interfaces produced:** `TapKeys(vks: tuple[int, ...])`, `Scroll(notches)`, `OpenUrl(url)`, `Action` union; constants `VK_LWIN=0x5B`, `VK_D=0x44`, `VK_VOLUME_UP=0xAF`, `VK_VOLUME_DOWN=0xAE`, `OPEN_START_MENU`, `SHOW_DESKTOP`, `VOLUME_UP`, `VOLUME_DOWN`; `InputBackend` gains `tap_keys(vks)` (replacing `tap_key`) and `open_url(url)`; `winput.tap_keys` sends all key-downs then key-ups in reverse in one `SendInput`; `winput.open_url` wraps `webbrowser.open` and logs on failure.

- [x] Tests: `TapKeys` maps to `tap_keys` with the same tuple; `OPEN_START_MENU` is `(VK_LWIN,)`, `SHOW_DESKTOP` is `(VK_LWIN, VK_D)`; `OpenUrl` maps to `open_url`; scroll tests unchanged.
- [x] Run to fail, implement, run to pass, commit `feat: key chords and open-url actions`.

### Task 2: Settings

**Files:** modify `handcontrol/config.py`; test `tests/test_config.py`.

**Interfaces produced:** `HandSettings` + `vertical_max_deg=35.0`, `min_direction_len=0.6`; `StartMenuSettings(max_distance_widths=1.2, hold_frames=8, cooldown_s=1.5)`; `YoutubeSettings(hold_frames=18, cooldown_s=2.0, url="https://www.youtube.com")`; `ShowDesktopSettings(hold_frames=18, cooldown_s=1.5)`; `VolumeSettings(engage_frames=10, repeat_frames=5)`; `ScrollSettings` with `deadzone_widths=0.02`, `gain_notches_per_width=3.0` (renamed); `Settings` sections `camera, tracker, hand, start_menu, youtube, show_desktop, volume, scroll`.

- [x] Update `test_defaults_match_spec` and the override tests to the new names; run to fail, implement, pass, commit `feat: settings for v1.1 gestures`.

### Task 3: Hand pose, scene and builder

**Files:** modify `handcontrol/hand.py`, `tests/handbuilder.py`; rewrite `tests/test_hand.py`.

**Interfaces produced:** `HandPose` fields per spec §3.2 (`hand_width`, `direction_deg`, `direction_len`, `pointing`; `palm_size` and `palm_facing_camera` removed); properties `is_open_hand`, `is_two_finger`, `is_rock_on`, `is_middle_finger`; `Scene(hands, t)` with `primary`, `single`, `pair`; `make_scene(poses, t)` sorts by width; `hand_width(landmarks)`, `direction(landmarks) -> (deg, len)`. Builder: `build_hand(extended, *, spread=False, direction="up"|"down"|"camera"|"side", center=(0.5,0.5), scale=1.25, handedness="Right")` rotating the world layout so image landmarks foreshorten naturally; `facing` removed. Builder hand width is `0.06 × scale` image units (0.075 by default).

- [x] Tests: flags for open/fist/two-finger/rock-on/middle-finger; `pointing` up/down/None (camera, side); `direction_len` small for "camera"; hand width invariant across directions and centres; two-finger point and palm centre follow `center`; scene ordering by width, `single` None with two hands, `pair` None with one.
- [x] Run to fail, implement, pass, commit `feat: hand direction, width unit and two-hand scene`.

### Task 4: Gesture engine on scenes, hold and repeat gestures, predicates

**Files:** modify `handcontrol/gestures/base.py`; create `handcontrol/gestures/poses.py`, `hold.py`, `repeat.py`; tests `tests/test_gesture_engine.py` (adapt), `tests/test_poses.py`, `tests/test_hold.py`, `tests/test_repeat.py`.

**Interfaces produced:** `Gesture.update(scene, t)`; `GestureEngine.update(scene, t)`; `Predicate = Callable[[Scene], bool]`; `clap(max_distance_widths) -> Predicate`, `rock_on`, `middle_finger`, `volume_up`, `volume_down`; `HoldGesture(name, predicate, action, hold_frames, cooldown_s)` with states `IDLE/HOLDING/RELEASE/COOLDOWN`; `RepeatGesture(name, predicate, action, engage_frames, repeat_frames)` with states `IDLE/ACTIVE`.

- [x] Tests (poses): clap true for two open hands 0.5 widths apart, false at 3 widths, false if one hand is a fist, false with one hand; rock-on/middle-finger use the primary hand even with a second hand present; volume_up true for a single open hand pointing up, false when two hands are visible, false pointing down or at the camera; volume_down mirror.
- [x] Tests (hold): fires exactly once after `hold_frames` true frames; a false frame before that restarts the count; holding past the fire does not refire; after release, refire only once the cooldown has elapsed; `engaged` during HOLDING and RELEASE; `reset()` returns to IDLE.
- [x] Tests (repeat): nothing before `engage_frames`; emits on engage and then every `repeat_frames`; a false frame ends it and a new engage is needed; `engaged` while ACTIVE.
- [x] Tests (engine): adapt FakeGesture to scenes.
- [x] Run to fail, implement, pass, commit `feat: hold/repeat gestures and scene predicates`.

### Task 5: Scroll on scenes, remove the swipe

**Files:** modify `handcontrol/gestures/two_finger_scroll.py`, `tests/test_two_finger_scroll.py`; delete `handcontrol/gestures/start_menu.py`, `tests/test_start_menu.py`.

- [x] Tests: same scenarios as v1.0 in hand-width units and via scenes (0.1 widths per frame × gain 3.0 = 0.3 notch/frame: 9 frames → −2, 11 frames → −3; remainder test with 0.2 widths/frame → [0, −1, 0, −1]); scroll uses the primary hand when a second smaller hand is present; engine test: scroll in progress resets a hold gesture.
- [x] Run to fail, implement, pass, delete swipe files, run full suite, commit `feat: scroll on scenes in hand-width units; remove swipe`.

### Task 6: Wiring, preview, docs, end-to-end

**Files:** modify `handcontrol/app.py`, `handcontrol/tracker.py` (default `num_hands=2`), `handcontrol/preview.py` (all hands, flags + pointing per hand), `README.md`; the v1.0 plan gets a superseded note.

- [x] `App._loop` builds the gesture list in spec order from settings, builds the scene from all detected hands, passes `raws` to the preview.
- [x] Timed end-to-end runs (console + preview, tray, missing camera) as in v1.0 Task 11.
- [x] README gesture table and config table updated; commit `feat: wire v1.1 gestures; README`.

### Task 7: Live tuning (user session)

- [ ] With `handcontrol --preview -v`: check flags and `pointing` for each pose; try each gesture; confirm a resting second hand does not block scroll and that approaching hands do not change the volume; tune thresholds and write them back to `config.py`, spec §6 and README.
