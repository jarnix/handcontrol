"""Scene predicates: which hand(s) a gesture looks at and what pose it needs.

- Clap uses the pair of visible hands.
- Rock-on and middle finger use the primary (larger) hand, so a resting second
  hand does not block them.
- Volume needs exactly one visible hand, so two open hands coming together for
  a clap never nudge the volume on the way in.
"""

from __future__ import annotations

from typing import Callable

from handcontrol.hand import Scene, distance

Predicate = Callable[[Scene], bool]


def clap(max_distance_widths: float) -> Predicate:
    """Two open hands whose palm centres are within ``max_distance_widths`` hand widths."""

    def predicate(scene: Scene) -> bool:
        pair = scene.pair
        if pair is None:
            return False
        a, b = pair
        if not (a.is_open_hand and b.is_open_hand):
            return False
        return distance(a.palm_center, b.palm_center) <= max_distance_widths * max(a.hand_width, b.hand_width)

    return predicate


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
