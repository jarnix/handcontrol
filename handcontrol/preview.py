"""Debug preview window: landmarks of every hand on the mirrored frame, pose flags, gesture states, fps."""

from __future__ import annotations

import time

import cv2
import numpy as np

from handcontrol.hand import HandPose, RawHand, Scene

WINDOW = "HandControl preview"
CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]
GREEN = (80, 200, 80)
WHITE = (255, 255, 255)
YELLOW = (0, 220, 255)


def pose_name(pose: HandPose) -> str:
    if pose.is_open_hand:
        return "open"
    if pose.is_two_finger:
        return "two_finger"
    if pose.is_rock_on:
        return "rock_on"
    if pose.is_middle_finger:
        return "middle"
    return "-"


class Preview:
    def __init__(self) -> None:
        self.is_open = False
        self._last_t = time.monotonic()
        self._fps = 0.0

    def draw(self, frame_bgr: np.ndarray, raws: list[RawHand], scene: Scene, states: dict[str, str]) -> None:
        now = time.monotonic()
        dt = now - self._last_t
        self._last_t = now
        if dt > 0:
            self._fps = 0.9 * self._fps + 0.1 / dt

        img = frame_bgr.copy()
        h, w = img.shape[:2]
        for raw in raws:
            pts = [(int(x * w), int(y * h)) for x, y, _ in raw.landmarks]
            for a, b in CONNECTIONS:
                cv2.line(img, pts[a], pts[b], GREEN, 2)
            for p in pts:
                cv2.circle(img, p, 4, WHITE, -1)
        img = cv2.flip(img, 1)  # mirror for the viewer; text is drawn after the flip so it reads normally

        lines = [f"{self._fps:4.1f} fps  hands={len(scene.hands)}"]
        for i, pose in enumerate(scene.hands):
            flags = " ".join(f.value[:2] + ("+" if on else "-") for f, on in pose.fingers.items())
            angles = " ".join(f"{f.value[:2]}{a:3.0f}" for f, a in pose.finger_angles.items())
            lines.append(f"hand{i} {flags}  pose={pose_name(pose)} joined={pose.two_fingers_joined}")
            lines.append(f"      angles {angles}")
            lines.append(f"      width={pose.hand_width:.3f} dir={pose.direction_deg:+.0f} len={pose.direction_len:.2f} pointing={pose.pointing}")
        if not scene.hands:
            lines.append("no hand")
        lines.extend(f"{name}: {state}" for name, state in states.items())
        for i, text in enumerate(lines):
            cv2.putText(img, text, (10, 24 + 22 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.6, YELLOW, 2, cv2.LINE_AA)

        cv2.imshow(WINDOW, img)
        cv2.waitKey(1)
        self.is_open = True

    def close(self) -> None:
        if not self.is_open:
            return
        try:
            cv2.destroyWindow(WINDOW)
        except cv2.error:
            pass
        self.is_open = False
