"""Actions produced by gestures. The executor that performs them lives here too (Task 7)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OpenStartMenu:
    """Press and release the Windows key."""


@dataclass(frozen=True)
class Scroll:
    """Mouse-wheel scroll by ``notches``; positive = wheel up (content moves down)."""

    notches: int


Action = OpenStartMenu | Scroll
