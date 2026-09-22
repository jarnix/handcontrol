"""Builds synthetic RawHand objects for unit tests (no camera, no MediaPipe).

World space is metres with the wrist at the origin; y grows downward like the
image, so the hand points "up" along -y and a curled finger folds toward +z.
Image landmarks are the world layout scaled by 1.25 around ``center``, so the
palm size (wrist -> middle MCP, 0.08 m) comes out at exactly 0.1 image units.

Handedness and mirroring: as measured on MediaPipe's sample photos (see
handcontrol.hand.palm_facing_camera), a hand labelled "Right" with its palm
toward the camera has the thumb on the image RIGHT, and a "Left" palm has it
on the image LEFT. The base layout below puts the thumb at negative x (a
"Left" palm); x is mirrored whenever the requested label/facing combination
needs the thumb on the other side.
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


def _step(p, d, k):
    return (p[0] + d[0] * k, p[1] + d[1] * k, p[2] + d[2] * k)


def build_hand(
    extended: frozenset[Finger] | set[Finger] = ALL_FINGERS,
    *,
    spread: bool = False,
    handedness: str = "Right",
    facing: bool = True,
    center: tuple[float, float] = (0.5, 0.5),
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
    mirror = (handedness == "Right") == facing
    sx = -1.25 if mirror else 1.25
    landmarks = [(center[0] + x * sx, center[1] + y * 1.25, z) for x, y, z in world]
    return RawHand(landmarks=landmarks, world=world, handedness=handedness, score=0.99)
