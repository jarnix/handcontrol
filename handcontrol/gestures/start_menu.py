"""Open palm facing the camera, swept upward -> OpenStartMenu."""

from __future__ import annotations

from collections import deque

from handcontrol.actions import Action, OpenStartMenu
from handcontrol.config import StartMenuSettings
from handcontrol.hand import HandPose


class StartMenuSwipe:
    name = "start_menu"

    def __init__(self, settings: StartMenuSettings) -> None:
        self.settings = settings
        self.state = "IDLE"
        self._samples: deque[tuple[float, float]] = deque()  # (t, palm centre y) inside the window
        self._cooldown_until = 0.0

    @property
    def engaged(self) -> bool:
        return self.state == "ARMED"

    def reset(self) -> None:
        self.state = "IDLE"
        self._samples.clear()

    def update(self, pose: HandPose | None, t: float) -> list[Action]:
        if self.state == "COOLDOWN":
            if t < self._cooldown_until:
                return []
            self.state = "IDLE"
        if pose is None or not pose.is_open_palm:
            self.reset()
            return []
        self.state = "ARMED"
        y = pose.palm_center[1]
        self._samples.append((t, y))
        while self._samples and t - self._samples[0][0] > self.settings.swipe_window_s:
            self._samples.popleft()
        lowest_y = max(sample_y for _, sample_y in self._samples)  # y grows downward
        if lowest_y - y >= self.settings.swipe_distance_palms * pose.palm_size:
            self.state = "COOLDOWN"
            self._cooldown_until = t + self.settings.swipe_cooldown_s
            self._samples.clear()
            return [OpenStartMenu()]
        return []
