"""Builds synthetic RawHand objects for unit tests (no camera, no MediaPipe).

The base layout is an upright hand in metres with the wrist at the origin and
y growing downward like the image, so the hand points "up" along -y and a
curled finger folds toward +z. ``direction`` rotates that layout rigidly
("down", "camera" = fingers toward the lens, "side" = fingers to the right),
and the image landmarks are the rotated x/y scaled by ``scale`` around
``center``, so foreshortening happens naturally: a hand pointing at the camera
has almost no wrist-to-knuckle length in the image, but its knuckle width
(index MCP to pinky MCP, 0.06 m -> 0.06 * scale image units) is unchanged.
"""

from __future__ import annotations

from handcontrol.hand import Finger, RawHand

ALL_FINGERS = frozenset(Finger)

_MCP_X = {Finger.INDEX: -0.02, Finger.MIDDLE: 0.0, Finger.RING: 0.02, Finger.PINKY: 0.04}
_JOINTS = {
    Finger.INDEX: (5, 6, 7, 8),
    Finger.MIDDLE: (9, 10, 11, 12),
    Finger.RING: (13, 14, 15, 16),
    Finger.PINKY: (17, 18, 19, 20),
}
_UP = (0.0, -1.0, 0.0)
_FOLD = (0.0, 0.0, 1.0)

_ROTATIONS = {
    "up": lambda x, y, z: (x, y, z),
    "down": lambda x, y, z: (x, -y, -z),      # 180 degrees about x
    "camera": lambda x, y, z: (x, -z, y),     # 90 degrees about x: up becomes toward the lens
    "side": lambda x, y, z: (-y, x, z),       # 90 degrees about z: up becomes right
}


def _step(p, d, k):
    return (p[0] + d[0] * k, p[1] + d[1] * k, p[2] + d[2] * k)


def build_hand(
    extended: frozenset[Finger] | set[Finger] = ALL_FINGERS,
    *,
    spread: bool = False,
    direction: str = "up",
    center: tuple[float, float] = (0.5, 0.5),
    scale: float = 1.25,
    handedness: str = "Right",
) -> RawHand:
    world = [(0.0, 0.0, 0.0)] * 21
    # Thumb: CMC(1), MCP(2), IP(3), TIP(4). Extended = pointing up-left; curled = folded across the palm.
    world[1] = (-0.03, -0.02, 0.0)
    world[2] = (-0.05, -0.05, 0.0)
    thumb_dir = (-0.6, -0.8, 0.0) if Finger.THUMB in extended else (0.8, -0.2, 0.2)
    world[3] = _step(world[2], thumb_dir, 0.03)
    world[4] = _step(world[3], thumb_dir, 0.03)
    for finger, (mcp, pip, dip, tip) in _JOINTS.items():
        base = (_MCP_X[finger], -0.08, 0.0)
        proximal = _UP
        if spread and finger is Finger.INDEX:
            proximal = (-0.4, -0.9, 0.0)
        if spread and finger is Finger.MIDDLE:
            proximal = (0.4, -0.9, 0.0)
        distal = proximal if finger in extended else _FOLD  # curled: 90 degrees at the PIP joint
        world[mcp] = base
        world[pip] = _step(base, proximal, 0.03)
        world[dip] = _step(world[pip], distal, 0.025)
        world[tip] = _step(world[pip], distal, 0.05)
    rotate = _ROTATIONS[direction]
    world = [rotate(*p) for p in world]
    landmarks = [(center[0] + x * scale, center[1] + y * scale, z) for x, y, z in world]
    return RawHand(landmarks=landmarks, world=world, handedness=handedness, score=0.99)
