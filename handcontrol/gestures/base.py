"""Gesture protocol and the engine that arbitrates between gestures."""

from __future__ import annotations

from typing import Protocol, Sequence

from handcontrol.actions import Action
from handcontrol.hand import HandPose


class Gesture(Protocol):
    name: str
    state: str

    @property
    def engaged(self) -> bool: ...

    def update(self, pose: HandPose | None, t: float) -> list[Action]: ...

    def reset(self) -> None: ...


class GestureEngine:
    """Runs gestures in priority order. An engaged gesture owns the hand: every
    other gesture is reset and skipped until it lets go."""

    def __init__(self, gestures: Sequence[Gesture]) -> None:
        self.gestures = list(gestures)

    def update(self, pose: HandPose | None, t: float) -> list[Action]:
        owner = next((g for g in self.gestures if g.engaged), None)
        actions: list[Action] = []
        for gesture in self.gestures:
            if owner is not None and gesture is not owner:
                gesture.reset()
                continue
            actions.extend(gesture.update(pose, t))
            if owner is None and gesture.engaged:
                owner = gesture
        return actions

    def reset(self) -> None:
        for gesture in self.gestures:
            gesture.reset()

    @property
    def states(self) -> dict[str, str]:
        return {g.name: g.state for g in self.gestures}
