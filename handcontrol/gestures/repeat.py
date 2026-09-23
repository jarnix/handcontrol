"""A pose held fires an action on engage and again every N frames while it stays held."""

from __future__ import annotations

from handcontrol.actions import Action
from handcontrol.gestures.poses import Predicate
from handcontrol.hand import Scene


class RepeatGesture:
    """States: IDLE (counting consecutive true frames) -> ACTIVE (repeating) -> IDLE once the
    predicate has been false for more than ``release_frames`` consecutive frames. Engaging
    is strict (one false frame restarts the count); staying active is tolerant, because
    the tracker drops or misreads the odd frame."""

    def __init__(
        self,
        name: str,
        predicate: Predicate,
        action: Action,
        engage_frames: int,
        repeat_frames: int,
        release_frames: int = 0,
    ) -> None:
        self.name = name
        self.predicate = predicate
        self.action = action
        self.engage_frames = engage_frames
        self.repeat_frames = repeat_frames
        self.release_frames = release_frames
        self.state = "IDLE"
        self._count = 0
        self._since_last = 0
        self._missing = 0

    @property
    def engaged(self) -> bool:
        return self.state == "ACTIVE"

    def reset(self) -> None:
        self.state = "IDLE"
        self._count = 0
        self._since_last = 0
        self._missing = 0

    def update(self, scene: Scene, t: float) -> list[Action]:
        match = self.predicate(scene)
        if self.state == "IDLE":
            if not match:
                self._count = 0
                return []
            self._count += 1
            if self._count < self.engage_frames:
                return []
            self.state = "ACTIVE"
            self._since_last = 0
            self._missing = 0
            return [self.action]
        # ACTIVE
        if not match:
            self._missing += 1
            if self._missing > self.release_frames:
                self.reset()
            return []
        self._missing = 0
        self._since_last += 1
        if self._since_last < self.repeat_frames:
            return []
        self._since_last = 0
        return [self.action]
