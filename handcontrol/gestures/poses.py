"""Scene predicates: which hand a gesture looks at and what pose it needs.

- Fist, open hand, rock-on and middle finger use the primary (larger) hand, so
  a resting second hand does not block them.
- Volume needs exactly one visible hand.
"""

from __future__ import annotations

from typing import Callable

from handcontrol.hand import Scene

Predicate = Callable[[Scene], bool]


def fist(scene: Scene) -> bool:
    hand = scene.primary
    return hand is not None and hand.is_fist


def open_hand(scene: Scene) -> bool:
    hand = scene.primary
    return hand is not None and hand.is_open_hand


def rock_on(scene: Scene) -> bool:
    hand = scene.primary
    return hand is not None and hand.is_rock_on


def middle_finger(scene: Scene) -> bool:
    hand = scene.primary
    return hand is not None and hand.is_middle_finger


def volume_up(scene: Scene) -> bool:
    hand = scene.single
    return hand is not None and hand.is_open_hand and hand.pointing == "up"


def volume_down(scene: Scene) -> bool:
    hand = scene.single
    return hand is not None and hand.is_open_hand and hand.pointing == "down"
