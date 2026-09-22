"""A pose held fires an action on engage and again every N frames while it stays held."""

from __future__ import annotations

from handcontrol.actions import Action
from handcontrol.gestures.poses import Predicate
from handcontrol.hand import Scene


class RepeatGesture:
    """States: IDLE (counting true frames) -> ACTIVE (repeating) -> IDLE on the first false frame."""

    def __init__(self, name: str, predicate: Predicate, action: Action, engage_frames: int, repeat_frames: int) -> None:
        self.name = name
        self.predicate = predicate
        self.action = action
        self.engage_frames = engage_frames
        self.repeat_frames = repeat_frames
        self.state = "IDLE"
        self._count = 0
        self._since_last = 0

    @property
    def engaged(self) -> bool:
        return self.state == "ACTIVE"

    def reset(self) -> None:
        self.state = "IDLE"
        self._count = 0
        self._since_last = 0

    def update(self, scene: Scene, t: float) -> list[Action]:
        if not self.predicate(scene):
            self.reset()
            return []
        if self.state == "IDLE":
            self._count += 1
            if self._count < self.engage_frames:
                return []
            self.state = "ACTIVE"
            self._since_last = 0
            return [self.action]
        self._since_last += 1
        if self._since_last < self.repeat_frames:
            return []
        self._since_last = 0
        return [self.action]
