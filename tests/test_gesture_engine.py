from handbuilder import build_hand

from handcontrol.actions import Scroll
from handcontrol.config import HandSettings
from handcontrol.gestures.base import GestureEngine
from handcontrol.hand import pose_from_raw

POSE = pose_from_raw(build_hand(), t=0.0, settings=HandSettings())


class FakeGesture:
    """Engages on the first non-None pose (if allowed) and emits Scroll(1) while engaged."""

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

    def update(self, pose, t):
        self.seen.append(pose)
        if self.engages and pose is not None:
            self._engaged = True
            self.state = "ENGAGED"
        return [Scroll(1)] if self._engaged else []

    def reset(self):
        self._engaged = False
        self.state = "IDLE"
        self.resets += 1


def test_every_gesture_sees_the_pose_when_nobody_is_engaged():
    a, b = FakeGesture("a"), FakeGesture("b")
    assert GestureEngine([a, b]).update(POSE, 0.0) == []
    assert a.seen == [POSE] and b.seen == [POSE]


def test_newly_engaged_gesture_starves_lower_priority_in_the_same_frame():
    a, b = FakeGesture("a", engages=True), FakeGesture("b")
    engine = GestureEngine([a, b])
    assert engine.update(POSE, 0.0) == [Scroll(1)]
    assert b.seen == [] and b.resets == 1


def test_engaged_lower_priority_gesture_starves_higher_priority():
    a, b = FakeGesture("a"), FakeGesture("b", engages=True)
    engine = GestureEngine([a, b])
    engine.update(POSE, 0.0)          # both run; b engages at the end of the frame
    engine.update(POSE, 0.1)          # b owns the hand now
    assert a.seen == [POSE] and a.resets == 1
    assert len(b.seen) == 2


def test_states_and_reset():
    a, b = FakeGesture("a", engages=True), FakeGesture("b")
    engine = GestureEngine([a, b])
    engine.update(POSE, 0.0)
    assert engine.states == {"a": "ENGAGED", "b": "IDLE"}
    engine.reset()
    assert engine.states == {"a": "IDLE", "b": "IDLE"}
    assert not a.engaged
