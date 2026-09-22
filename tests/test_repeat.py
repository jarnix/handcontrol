from handcontrol.actions import VOLUME_UP
from handcontrol.gestures.repeat import RepeatGesture
from handcontrol.hand import Scene

SCENE = Scene(hands=(), t=0.0)
FPS = 30.0


def make(engage_frames=3, repeat_frames=2):
    flag = {"on": False}
    gesture = RepeatGesture("g", lambda scene: flag["on"], VOLUME_UP, engage_frames=engage_frames, repeat_frames=repeat_frames)
    return gesture, flag


def run(gesture, flag, pattern, t0=0.0):
    out = []
    for i, ch in enumerate(pattern):
        flag["on"] = ch == "T"
        out.append(gesture.update(SCENE, t0 + i / FPS))
    return out


def test_nothing_before_engage_frames():
    g, flag = make()
    assert run(g, flag, "TT") == [[], []]
    assert not g.engaged and g.state == "IDLE"


def test_emits_on_engage_then_every_repeat_frames():
    g, flag = make(engage_frames=3, repeat_frames=2)
    per_frame = run(g, flag, "T" * 9)
    assert per_frame == [[], [], [VOLUME_UP], [], [VOLUME_UP], [], [VOLUME_UP], [], [VOLUME_UP]]
    assert g.engaged and g.state == "ACTIVE"


def test_a_false_frame_ends_the_repeat_and_needs_a_new_engage():
    g, flag = make()
    assert run(g, flag, "TTTFTT") == [[], [], [VOLUME_UP], [], [], []]
    assert not g.engaged
    assert run(g, flag, "T", t0=1.0) == [[VOLUME_UP]]


def test_repeat_every_frame_when_repeat_frames_is_one():
    g, flag = make(engage_frames=1, repeat_frames=1)
    assert run(g, flag, "TTT") == [[VOLUME_UP], [VOLUME_UP], [VOLUME_UP]]


def test_reset_stops_an_active_repeat():
    g, flag = make()
    run(g, flag, "TTT")
    g.reset()
    assert g.state == "IDLE" and not g.engaged
    assert run(g, flag, "TT", t0=1.0) == [[], []]
