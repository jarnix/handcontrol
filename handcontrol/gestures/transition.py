"""A start pose held briefly and then turned into an end pose fires one action (e.g. fist -> open hand)."""

from __future__ import annotations

from handcontrol.actions import Action
from handcontrol.gestures.poses import Predicate
from handcontrol.hand import Scene


class TransitionGesture:
    """States: IDLE (counting start-pose frames) -> ARMED (start held long enough) ->
    RELEASE (fired, end pose still held) -> COOLDOWN (end pose released, waiting
    out cooldown_s since the fire) -> IDLE. While ARMED, up to
    ``max_transition_frames`` frames may show neither pose (the fingers in
    motion); returning to the start pose restarts that allowance."""

    def __init__(
        self,
        name: str,
        start: Predicate,
        end: Predicate,
        action: Action,
        min_start_frames: int,
        max_transition_frames: int,
        cooldown_s: float,
    ) -> None:
        self.name = name
        self.start = start
        self.end = end
        self.action = action
        self.min_start_frames = min_start_frames
        self.max_transition_frames = max_transition_frames
        self.cooldown_s = cooldown_s
        self.state = "IDLE"
        self._start_count = 0
        self._transition_count = 0
        self._fired_at = float("-inf")

    @property
    def engaged(self) -> bool:
        return self.state in ("ARMED", "RELEASE")

    def reset(self) -> None:
        self.state = "IDLE"
        self._start_count = 0
        self._transition_count = 0

    def update(self, scene: Scene, t: float) -> list[Action]:
        at_start = self.start(scene)
        at_end = self.end(scene)
        if self.state == "RELEASE":
            if at_end:
                return []
            self.state = "COOLDOWN"
        if self.state == "COOLDOWN":
            if t < self._fired_at + self.cooldown_s:
                return []
            self.state = "IDLE"
        if self.state == "IDLE":
            if not at_start:
                self._start_count = 0
                return []
            self._start_count += 1
            if self._start_count >= self.min_start_frames:
                self.state = "ARMED"
                self._transition_count = 0
            return []
        # ARMED
        if at_end:
            self.state = "RELEASE"
            self._fired_at = t
            self._start_count = 0
            self._transition_count = 0
            return [self.action]
        if at_start:
            self._transition_count = 0
            return []
        self._transition_count += 1
        if self._transition_count > self.max_transition_frames:
            self.reset()
        return []
