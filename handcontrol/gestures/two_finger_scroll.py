"""Index + middle finger joined, moved vertically -> Scroll (natural direction)."""

from __future__ import annotations

from handcontrol.actions import Action, Scroll
from handcontrol.config import ScrollSettings
from handcontrol.hand import HandPose


class TwoFingerScroll:
    name = "scroll"

    def __init__(self, settings: ScrollSettings) -> None:
        self.settings = settings
        self.state = "IDLE"
        self._held_frames = 0
        self._missing_frames = 0
        self._prev_y = 0.0
        self._velocity = 0.0      # smoothed, palm units per frame, positive = fingers moving down
        self._notches_acc = 0.0   # fractional wheel notches not yet emitted

    @property
    def engaged(self) -> bool:
        return self.state == "TRACKING"

    def reset(self) -> None:
        self.state = "IDLE"
        self._held_frames = 0
        self._missing_frames = 0
        self._velocity = 0.0
        self._notches_acc = 0.0

    def update(self, pose: HandPose | None, t: float) -> list[Action]:
        present = pose is not None and pose.is_two_finger
        if self.state == "IDLE":
            if not present:
                self._held_frames = 0
                return []
            self._held_frames += 1
            if self._held_frames >= self.settings.engage_frames:
                self.state = "TRACKING"
                self._prev_y = pose.two_finger_point[1]
                self._missing_frames = 0
                self._velocity = 0.0
                self._notches_acc = 0.0
            return []

        # TRACKING
        if not present:
            self._missing_frames += 1
            if self._missing_frames > self.settings.release_frames:
                self.reset()
            return []
        self._missing_frames = 0
        y = pose.two_finger_point[1]
        dy = (y - self._prev_y) / pose.palm_size
        self._prev_y = y
        s = self.settings.smoothing
        self._velocity = s * self._velocity + (1.0 - s) * dy
        if abs(self._velocity) < self.settings.deadzone_palms:
            return []
        # Fingers down (dy > 0) -> content moves down -> wheel up (positive). Natural scrolling.
        self._notches_acc += self._velocity * self.settings.gain_notches_per_palm
        notches = int(self._notches_acc)  # truncates toward zero, remainder stays in the accumulator
        if notches == 0:
            return []
        self._notches_acc -= notches
        return [Scroll(notches)]
