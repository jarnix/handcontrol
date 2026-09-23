from handbuilder import build_hand

from handcontrol.actions import SHOW_DESKTOP, Scroll
from handcontrol.config import HandSettings, ScrollSettings
from handcontrol.gestures.base import GestureEngine
from handcontrol.gestures.hold import HoldGesture
from handcontrol.gestures.poses import middle_finger
from handcontrol.gestures.two_finger_scroll import TwoFingerScroll
from handcontrol.hand import Finger, make_scene, pose_from_raw

FPS = 30.0
H = HandSettings()
EXACT = ScrollSettings(smoothing=0.0, deadzone_widths=0.0)  # deterministic: no EMA, no dead zone
WIDTH = 0.06 * 1.25  # builder hand width in image units at the default scale


def two_finger(y, scale=1.25):
    return pose_from_raw(build_hand(extended={Finger.INDEX, Finger.MIDDLE}, center=(0.5, y), scale=scale), 0.0, H)


def open_hand(y=0.5, scale=1.25, x=0.5):
    return pose_from_raw(build_hand(center=(x, y), scale=scale), 0.0, H)


def scene(*poses):
    return make_scene(poses, 0.0)


def run(gesture, scenes, t0=0.0):
    actions = []
    for i, s in enumerate(scenes):
        actions.extend(gesture.update(s, t0 + i / FPS))
    return actions


def moving(y0, step, frames):
    """Scenes with one two-finger hand starting one step after y0, moving by ``step`` per frame."""
    return [scene(two_finger(y0 + step * i)) for i in range(1, frames + 1)]


def total(actions):
    assert all(isinstance(a, Scroll) for a in actions)
    return sum(a.notches for a in actions)


def engaged_gesture(settings=EXACT, y=0.6):
    g = TwoFingerScroll(settings)
    run(g, [scene(two_finger(y))] * settings.engage_frames)
    assert g.engaged
    return g


def test_needs_engage_frames_before_tracking():
    g = TwoFingerScroll(EXACT)
    run(g, [scene(two_finger(0.5))] * 2)
    assert not g.engaged and g.state == "IDLE"
    run(g, [scene(two_finger(0.5))], t0=0.1)
    assert g.engaged and g.state == "TRACKING"


def test_hold_must_be_consecutive():
    g = TwoFingerScroll(EXACT)
    tf = scene(two_finger(0.5))
    run(g, [tf, tf, scene(), tf, tf])
    assert not g.engaged


def test_moving_up_scrolls_down_natural_direction():
    g = engaged_gesture()
    # 0.1 widths per frame upward (y decreasing), gain 3 -> 0.3 notch/frame.
    assert total(run(g, moving(0.6, -0.1 * WIDTH, 9), t0=1.0)) == -2      # 2.7 -> 2 emitted
    assert total(run(g, moving(0.6 - 0.9 * WIDTH, -0.1 * WIDTH, 2), t0=2.0)) == -1   # 3.3 total -> 3


def test_moving_down_scrolls_up():
    g = engaged_gesture(y=0.4)
    assert total(run(g, moving(0.4, 0.1 * WIDTH, 11), t0=1.0)) == 3


def test_fractional_remainder_carries_across_frames():
    g = engaged_gesture()
    # 0.2 widths per frame -> 0.6 notch per frame: acc -0.6, -1.2 (emit -1), -0.8, -1.4 (emit -1)
    per_frame = [total(g.update(s, 1.0 + i / FPS)) for i, s in enumerate(moving(0.6, -0.2 * WIDTH, 4))]
    assert per_frame == [0, -1, 0, -1]


def test_dead_zone_swallows_jitter():
    g = engaged_gesture(ScrollSettings(smoothing=0.0))   # default dead zone 0.02 widths
    step = 0.005 * WIDTH
    jitter = [scene(two_finger(0.6 + (step if i % 2 else -step))) for i in range(30)]  # 0.01 widths/frame
    assert run(g, jitter, t0=1.0) == []


def test_default_smoothing_keeps_direction_and_magnitude_close():
    g = engaged_gesture(ScrollSettings())
    actions = run(g, moving(0.6, -0.1 * WIDTH, 11), t0=1.0)
    assert all(a.notches < 0 for a in actions)
    assert -3 <= total(actions) <= -1


def test_one_frame_flicker_keeps_tracking():
    g = engaged_gesture()
    g.update(scene(), 1.0)
    assert g.engaged
    assert total(run(g, moving(0.6, -0.1 * WIDTH, 11), t0=1.1)) == -3


def test_losing_the_hand_beyond_release_frames_resets():
    g = engaged_gesture()
    run(g, [scene()] * 5, t0=1.0)
    assert g.engaged
    run(g, [scene()], t0=1.2)
    assert not g.engaged and g.state == "IDLE"


def test_open_hand_is_not_a_scroll_pose():
    g = TwoFingerScroll(EXACT)
    run(g, [scene(open_hand())] * 5)
    assert not g.engaged


def test_uses_the_larger_hand_when_a_second_hand_rests_in_view():
    g = TwoFingerScroll(EXACT)
    small = open_hand(scale=1.0, x=0.9)
    big_width = 0.06 * 2.0
    run(g, [scene(two_finger(0.6, scale=2.0), small)] * 3)
    assert g.engaged
    frames = [scene(two_finger(0.6 - 0.1 * big_width * i, scale=2.0), small) for i in range(1, 12)]
    assert total(run(g, frames, t0=1.0)) == -3


def test_engine_scroll_in_progress_blocks_a_hold_gesture():
    hold = HoldGesture("desk", middle_finger, SHOW_DESKTOP, hold_frames=3, cooldown_s=1.0)
    engine = GestureEngine([TwoFingerScroll(EXACT), hold])
    for i in range(3):
        engine.update(scene(two_finger(0.6)), i / FPS)
    assert engine.states["scroll"] == "TRACKING"
    middle = pose_from_raw(build_hand(extended={Finger.MIDDLE}), 0.0, H)
    actions = []
    for i in range(5):  # inside the scroll release window the hold gesture is reset every frame
        actions.extend(engine.update(scene(middle), 0.1 + i / FPS))
    assert actions == []
