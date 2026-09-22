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
