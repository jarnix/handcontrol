from handcontrol.actions import OpenUrl
from handcontrol.gestures.hold import HoldGesture
from handcontrol.hand import Scene

ACTION = OpenUrl("https://example.com")
SCENE = Scene(hands=(), t=0.0)  # the fake predicate ignores the scene
FPS = 30.0


def make(hold_frames=3, cooldown_s=1.0):
    flag = {"on": False}
    gesture = HoldGesture("g", lambda scene: flag["on"], ACTION, hold_frames=hold_frames, cooldown_s=cooldown_s)
    return gesture, flag


def run(gesture, flag, pattern, t0=0.0):
    """Feed a string of T/F frames at 30 fps; return the actions emitted per frame."""
    out = []
    for i, ch in enumerate(pattern):
        flag["on"] = ch == "T"
        out.append(gesture.update(SCENE, t0 + i / FPS))
    return out


def fires(per_frame):
    return sum(len(a) for a in per_frame)


def test_fires_exactly_once_after_hold_frames():
    g, flag = make()
    assert run(g, flag, "TTTTT") == [[], [], [ACTION], [], []]
    assert g.state == "RELEASE" and g.engaged


def test_a_false_frame_restarts_the_count():
    g, flag = make()
    assert fires(run(g, flag, "TTFTT")) == 0
    assert fires(run(g, flag, "T", t0=1.0)) == 1


def test_holding_past_the_fire_does_not_refire():
    g, flag = make()
    assert fires(run(g, flag, "T" * 60)) == 1


def test_refires_only_after_release_and_cooldown():
    g, flag = make(hold_frames=3, cooldown_s=1.0)
    assert fires(run(g, flag, "TTT")) == 1                     # fires at t = 0.067
    assert fires(run(g, flag, "F" + "TTT", t0=0.1)) == 0       # released, but still inside the cooldown
    assert g.state == "COOLDOWN" and not g.engaged
    assert fires(run(g, flag, "TTT", t0=2.0)) == 1             # cooldown over: a fresh hold fires again


def test_release_after_the_cooldown_already_expired_rearms_immediately():
    g, flag = make(hold_frames=3, cooldown_s=1.0)
    run(g, flag, "TTT")
    run(g, flag, "T" * 40, t0=0.1)                             # held for 1.3 s, past the cooldown
    assert fires(run(g, flag, "F" + "TTT", t0=2.0)) == 1


def test_engaged_only_while_holding_or_waiting_for_release():
    g, flag = make()
    assert not g.engaged and g.state == "IDLE"
    run(g, flag, "T")
    assert g.engaged and g.state == "HOLDING"
    run(g, flag, "TT", t0=0.1)
    assert g.engaged and g.state == "RELEASE"
    run(g, flag, "F", t0=0.2)
    assert not g.engaged and g.state == "COOLDOWN"


def test_reset_clears_a_hold_in_progress():
    g, flag = make()
    run(g, flag, "TT")
    g.reset()
    assert g.state == "IDLE" and not g.engaged
    assert run(g, flag, "TTT", t0=1.0) == [[], [], [ACTION]]
