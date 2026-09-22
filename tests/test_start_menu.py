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
    # Same image-space rise (0.12 = 1.2 palms) fires at 1.0 palm, not at 1.5.
    g = StartMenuSwipe(StartMenuSettings(swipe_distance_palms=1.0))
    assert run(g, rising(0.62, 0.5, 6)) == [OpenStartMenu()]
    g2 = StartMenuSwipe(StartMenuSettings(swipe_distance_palms=1.5))
    assert run(g2, rising(0.62, 0.5, 6)) == []
