"""Pure geometry: turn 21 MediaPipe hand landmarks into a HandPose, and group poses into a Scene.

Landmark indices follow MediaPipe: 0 wrist; thumb 1-4 (CMC, MCP, IP, TIP);
index 5-8, middle 9-12, ring 13-16, pinky 17-20 (MCP, PIP, DIP, TIP).
Image landmarks are normalized 0..1 with y growing downward. World landmarks
are metres, centred on the hand, and are used for anything that must not
depend on distance or camera angle (finger bend, fingertip spacing).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Literal, Mapping

from handcontrol.config import HandSettings

Point3 = tuple[float, float, float]
Point2 = tuple[float, float]
Pointing = Literal["up", "down"] | None

WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20


class Finger(Enum):
    THUMB = "thumb"
    INDEX = "index"
    MIDDLE = "middle"
    RING = "ring"
    PINKY = "pinky"


# (root, bending joint, tip): the angle at the bending joint says whether the finger is straight.
FINGER_JOINTS: dict[Finger, tuple[int, int, int]] = {
    Finger.THUMB: (THUMB_CMC, THUMB_MCP, THUMB_TIP),
    Finger.INDEX: (INDEX_MCP, INDEX_PIP, INDEX_TIP),
    Finger.MIDDLE: (MIDDLE_MCP, MIDDLE_PIP, MIDDLE_TIP),
    Finger.RING: (RING_MCP, RING_PIP, RING_TIP),
    Finger.PINKY: (PINKY_MCP, PINKY_PIP, PINKY_TIP),
}


@dataclass(frozen=True)
class RawHand:
    landmarks: list[Point3]
    world: list[Point3]
    handedness: str
    score: float


@dataclass(frozen=True)
class HandPose:
    fingers: Mapping[Finger, bool]
    hand_width: float          # image-space index MCP <-> pinky MCP; the unit for motion thresholds
    palm_center: Point2        # image space
    two_finger_point: Point2   # midpoint of index and middle tips, image space
    two_fingers_joined: bool   # index tip <-> middle tip within a few cm (world space)
    direction_deg: float       # image-space wrist -> middle MCP: 0 up, 90 right, +-180 down, -90 left
    direction_len: float       # |wrist -> middle MCP| in hand widths; small = fingers toward the camera
    pointing: Pointing         # "up" / "down" when clearly vertical, else None
    t: float

    def _only(self, *extended: Finger) -> bool:
        """True when exactly these fingers (thumb ignored) are extended."""
        return all(self.fingers[f] == (f in extended) for f in Finger if f is not Finger.THUMB)

    @property
    def is_open_hand(self) -> bool:
        return self._only(Finger.INDEX, Finger.MIDDLE, Finger.RING, Finger.PINKY)

    @property
    def is_two_finger(self) -> bool:
        return self._only(Finger.INDEX, Finger.MIDDLE) and self.two_fingers_joined

    @property
    def is_rock_on(self) -> bool:
        return self._only(Finger.INDEX, Finger.PINKY)

    @property
    def is_middle_finger(self) -> bool:
        return self._only(Finger.MIDDLE)


@dataclass(frozen=True)
class Scene:
    """Every hand visible in one frame, largest first."""

    hands: tuple[HandPose, ...]
    t: float

    @property
    def primary(self) -> HandPose | None:
        return self.hands[0] if self.hands else None

    @property
    def single(self) -> HandPose | None:
        return self.hands[0] if len(self.hands) == 1 else None

    @property
    def pair(self) -> tuple[HandPose, HandPose] | None:
        return (self.hands[0], self.hands[1]) if len(self.hands) >= 2 else None


def make_scene(poses: Iterable[HandPose], t: float) -> Scene:
    ordered = sorted(poses, key=lambda p: p.hand_width, reverse=True)
    return Scene(hands=tuple(ordered[:2]), t=t)


def distance(a, b) -> float:
    return math.dist(a, b)


def angle_deg(a: Point3, b: Point3, c: Point3) -> float:
    """Angle at ``b`` in degrees between rays b->a and b->c; 180 means straight."""
    bax, bay, baz = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    bcx, bcy, bcz = c[0] - b[0], c[1] - b[1], c[2] - b[2]
    na = math.sqrt(bax * bax + bay * bay + baz * baz)
    nc = math.sqrt(bcx * bcx + bcy * bcy + bcz * bcz)
    if na == 0.0 or nc == 0.0:
        return 0.0
    cos = (bax * bcx + bay * bcy + baz * bcz) / (na * nc)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


def finger_extended(world: list[Point3], finger: Finger, min_angle_deg: float) -> bool:
    root, joint, tip = FINGER_JOINTS[finger]
    return angle_deg(world[root], world[joint], world[tip]) >= min_angle_deg


def hand_width(landmarks: list[Point3]) -> float:
    """Image-space knuckle width (index MCP <-> pinky MCP). Stays visible whichever way the fingers point."""
    return distance(landmarks[INDEX_MCP][:2], landmarks[PINKY_MCP][:2])


def palm_center(landmarks: list[Point3]) -> Point2:
    idx = (WRIST, INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP)
    return (sum(landmarks[i][0] for i in idx) / 5, sum(landmarks[i][1] for i in idx) / 5)


def direction(landmarks: list[Point3], width: float) -> tuple[float, float]:
    """(angle in degrees, length in hand widths) of the image-space wrist -> middle MCP vector.

    Angle: 0 = fingers up, 90 = right, +-180 = down, -90 = left. Length near 0
    means the hand is foreshortened (fingers toward or away from the camera).
    """
    dx = landmarks[MIDDLE_MCP][0] - landmarks[WRIST][0]
    dy = landmarks[MIDDLE_MCP][1] - landmarks[WRIST][1]
    deg = math.degrees(math.atan2(dx, -dy)) if (dx or dy) else 0.0
    length = math.hypot(dx, dy) / width if width > 0 else 0.0
    return deg, length


def pointing(direction_deg: float, direction_len: float, settings: HandSettings) -> Pointing:
    if direction_len < settings.min_direction_len:
        return None
    if abs(direction_deg) <= settings.vertical_max_deg:
        return "up"
    if 180.0 - abs(direction_deg) <= settings.vertical_max_deg:
        return "down"
    return None


def pose_from_raw(raw: RawHand, t: float, settings: HandSettings) -> HandPose:
    fingers = {f: finger_extended(raw.world, f, settings.finger_extended_angle_deg) for f in Finger}
    index_tip, middle_tip = raw.landmarks[INDEX_TIP], raw.landmarks[MIDDLE_TIP]
    width = hand_width(raw.landmarks)
    deg, length = direction(raw.landmarks, width)
    return HandPose(
        fingers=fingers,
        hand_width=width,
        palm_center=palm_center(raw.landmarks),
        two_finger_point=((index_tip[0] + middle_tip[0]) / 2, (index_tip[1] + middle_tip[1]) / 2),
        two_fingers_joined=distance(raw.world[INDEX_TIP], raw.world[MIDDLE_TIP]) <= settings.fingers_joined_max_m,
        direction_deg=deg,
        direction_len=length,
        pointing=pointing(deg, length, settings),
        t=t,
    )
