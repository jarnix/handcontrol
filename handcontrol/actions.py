"""Actions produced by gestures, and the executor that performs them."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class OpenStartMenu:
    """Press and release the Windows key."""


@dataclass(frozen=True)
class Scroll:
    """Mouse-wheel scroll by ``notches``; positive = wheel up (content moves down)."""

    notches: int


Action = OpenStartMenu | Scroll

VK_LWIN = 0x5B  # left Windows key virtual-key code


class InputBackend(Protocol):
    def tap_key(self, vk: int) -> None: ...

    def scroll_wheel(self, delta: int) -> None: ...

    def cursor_pos(self) -> tuple[int, int]: ...

    def set_cursor_pos(self, x: int, y: int) -> None: ...

    def foreground_window_rect(self) -> tuple[int, int, int, int] | None: ...


class ActionExecutor:
    """Performs actions through an InputBackend (the ``winput`` module in production)."""

    def __init__(self, backend: InputBackend, wheel_step: int = 120) -> None:
        self.backend = backend
        self.wheel_step = wheel_step

    def execute(self, action: Action) -> None:
        match action:
            case OpenStartMenu():
                self.backend.tap_key(VK_LWIN)
            case Scroll(notches):
                self._ensure_cursor_in_foreground_window()
                self.backend.scroll_wheel(notches * self.wheel_step)
            case _:
                log.warning("unknown action %r", action)

    def _ensure_cursor_in_foreground_window(self) -> None:
        """Windows delivers wheel events to the window under the cursor, so park the
        cursor inside the focused window when it is somewhere else."""
        rect = self.backend.foreground_window_rect()
        if rect is None:
            return
        left, top, right, bottom = rect
        x, y = self.backend.cursor_pos()
        if not (left <= x < right and top <= y < bottom):
            self.backend.set_cursor_pos((left + right) // 2, (top + bottom) // 2)
