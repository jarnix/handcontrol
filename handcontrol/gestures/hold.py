"""A pose held for N consecutive frames fires one action; release and cooldown before the next."""

from __future__ import annotations

from handcontrol.actions import Action
from handcontrol.gestures.poses import Predicate
from handcontrol.hand import Scene


class HoldGesture:
    """States: IDLE -> HOLDING (counting true frames) -> RELEASE (fired, pose still
    held) -> COOLDOWN (released, waiting out cooldown_s since the fire) -> IDLE."""

    def __init__(self, name: str, predicate: Predicate, action: Action, hold_frames: int, cooldown_s: float) -> None:
        self.name = name
        self.predicate = predicate
        self.action = action
        self.hold_frames = hold_frames
        self.cooldown_s = cooldown_s
        self.state = "IDLE"
        self._count = 0
        self._fired_at = float("-inf")

    @property
    def engaged(self) -> bool:
        return self.state in ("HOLDING", "RELEASE")

    def reset(self) -> None:
        self.state = "IDLE"
        self._count = 0

    def update(self, scene: Scene, t: float) -> list[Action]:
        match = self.predicate(scene)
        if self.state == "RELEASE":
            if match:
                return []
            self.state = "COOLDOWN"
        if self.state == "COOLDOWN":
            if t < self._fired_at + self.cooldown_s:
                return []
            self.state = "IDLE"
        if not match:
            self.state = "IDLE"
            self._count = 0
            return []
        self._count += 1
        self.state = "HOLDING"
        if self._count < self.hold_frames:
            return []
        self.state = "RELEASE"
        self._fired_at = t
        self._count = 0
        return [self.action]
