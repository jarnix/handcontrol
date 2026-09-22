from handbuilder import build_hand

from handcontrol.actions import Scroll
from handcontrol.config import HandSettings
from handcontrol.gestures.base import GestureEngine
from handcontrol.hand import make_scene, pose_from_raw

SCENE = make_scene([pose_from_raw(build_hand(), t=0.0, settings=HandSettings())], 0.0)


class FakeGesture:
    """Engages on the first scene with a hand (if allowed) and emits Scroll(1) while engaged."""

    def __init__(self, name, engages=False):
        self.name = name
        self.engages = engages
        self.state = "IDLE"
        self._engaged = False
        self.seen = []
        self.resets = 0

    @property
    def engaged(self):
        return self._engaged

    def update(self, scene, t):
        self.seen.append(scene)
        if self.engages and scene.hands:
            self._engaged = True
            self.state = "ENGAGED"
        return [Scroll(1)] if self._engaged else []

    def reset(self):
        self._engaged = False
        self.state = "IDLE"
        self.resets += 1


def test_every_gesture_sees_the_scene_when_nobody_is_engaged():
    a, b = FakeGesture("a"), FakeGesture("b")
    assert GestureEngine([a, b]).update(SCENE, 0.0) == []
    assert a.seen == [SCENE] and b.seen == [SCENE]


def test_newly_engaged_gesture_starves_lower_priority_in_the_same_frame():
    a, b = FakeGesture("a", engages=True), FakeGesture("b")
    engine = GestureEngine([a, b])
    assert engine.update(SCENE, 0.0) == [Scroll(1)]
    assert b.seen == [] and b.resets == 1


def test_engaged_lower_priority_gesture_starves_higher_priority():
    a, b = FakeGesture("a"), FakeGesture("b", engages=True)
    engine = GestureEngine([a, b])
    engine.update(SCENE, 0.0)          # both run; b engages at the end of the frame
    engine.update(SCENE, 0.1)          # b owns the hand now
    assert a.seen == [SCENE] and a.resets == 1
    assert len(b.seen) == 2


def test_states_and_reset():
    a, b = FakeGesture("a", engages=True), FakeGesture("b")
    engine = GestureEngine([a, b])
    engine.update(SCENE, 0.0)
    assert engine.states == {"a": "ENGAGED", "b": "IDLE"}
    engine.reset()
    assert engine.states == {"a": "IDLE", "b": "IDLE"}
    assert not a.engaged
