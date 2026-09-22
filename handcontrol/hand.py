"""Pure geometry: turn 21 MediaPipe hand landmarks into a HandPose.

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
from typing import Mapping

from handcontrol.config import HandSettings

Point3 = tuple[float, float, float]
Point2 = tuple[float, float]

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

FOUR_FINGERS = (Finger.INDEX, Finger.MIDDLE, Finger.RING, Finger.PINKY)


@dataclass(frozen=True)
class RawHand:
    landmarks: list[Point3]
    world: list[Point3]
    handedness: str
    score: float


@dataclass(frozen=True)
class HandPose:
    fingers: Mapping[Finger, bool]
    palm_facing_camera: bool
    palm_size: float
    palm_center: Point2
    two_finger_point: Point2
    two_fingers_joined: bool
    t: float

    @property
    def is_open_palm(self) -> bool:
        """Index..pinky extended and palm toward the camera. The thumb is ignored on purpose."""
        return self.palm_facing_camera and all(self.fingers[f] for f in FOUR_FINGERS)

    @property
    def is_two_finger(self) -> bool:
        return (
            self.fingers[Finger.INDEX]
            and self.fingers[Finger.MIDDLE]
            and self.two_fingers_joined
            and not self.fingers[Finger.RING]
            and not self.fingers[Finger.PINKY]
        )


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


def palm_facing_camera(landmarks: list[Point3], handedness: str) -> bool:
    """True when the palm, not the back of the hand, faces the camera.

    Uses the 2-D cross product of wrist->index_mcp and wrist->pinky_mcp in
    image space (y down). The sign convention was measured on MediaPipe's own
    sample photos (gesture_recognizer/victory.jpg and pointing_up.jpg, both
    palms toward the camera): a hand labelled "Right" with its palm visible
    has the thumb on the image RIGHT, so index_mcp sits right of pinky_mcp and
    the cross product is negative; a "Left" palm mirrors that. The back of a
    hand flips the sign. Note this is the opposite of what the MediaPipe docs'
    "labels assume a mirrored image" remark suggests; the measurement wins,
    and it is re-checked live in the preview window (plan Task 12).
    """
    w, i, p = landmarks[WRIST], landmarks[INDEX_MCP], landmarks[PINKY_MCP]
    ux, uy = i[0] - w[0], i[1] - w[1]
    vx, vy = p[0] - w[0], p[1] - w[1]
    z = ux * vy - uy * vx
    return z < 0 if handedness == "Right" else z > 0


def palm_size(landmarks: list[Point3]) -> float:
    """Image-space wrist -> middle MCP distance; the unit for all motion thresholds."""
    return distance(landmarks[WRIST][:2], landmarks[MIDDLE_MCP][:2])


def palm_center(landmarks: list[Point3]) -> Point2:
    idx = (WRIST, INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP)
    return (sum(landmarks[i][0] for i in idx) / 5, sum(landmarks[i][1] for i in idx) / 5)


def pose_from_raw(raw: RawHand, t: float, settings: HandSettings) -> HandPose:
    fingers = {f: finger_extended(raw.world, f, settings.finger_extended_angle_deg) for f in Finger}
    index_tip, middle_tip = raw.landmarks[INDEX_TIP], raw.landmarks[MIDDLE_TIP]
    return HandPose(
        fingers=fingers,
        palm_facing_camera=palm_facing_camera(raw.landmarks, raw.handedness),
        palm_size=palm_size(raw.landmarks),
        palm_center=palm_center(raw.landmarks),
        two_finger_point=((index_tip[0] + middle_tip[0]) / 2, (index_tip[1] + middle_tip[1]) / 2),
        two_fingers_joined=distance(raw.world[INDEX_TIP], raw.world[MIDDLE_TIP]) <= settings.fingers_joined_max_m,
        t=t,
    )
