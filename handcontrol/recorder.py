"""Per-frame JSON Lines recording of what the pipeline sees, for offline gesture diagnosis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from handcontrol.actions import Action
from handcontrol.hand import HandPose, Scene


def pose_name(pose: HandPose) -> str:
    if pose.is_open_hand:
        return "open"
    if pose.is_fist:
        return "fist"
    if pose.is_two_finger:
        return "two_finger"
    if pose.is_rock_on:
        return "rock_on"
    if pose.is_middle_finger:
        return "middle"
    return "-"


def hand_record(pose: HandPose) -> dict:
    return {
        "fingers": {f.value: on for f, on in pose.fingers.items()},
        "pose": pose_name(pose),
        "pointing": pose.pointing,
        "direction_deg": round(pose.direction_deg, 1),
        "direction_len": round(pose.direction_len, 3),
        "width": round(pose.hand_width, 4),
        "palm_center": [round(pose.palm_center[0], 4), round(pose.palm_center[1], 4)],
        "joined": pose.two_fingers_joined,
    }


class Recorder:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._file = path.open("w", encoding="utf-8")

    def record(self, scene: Scene, states: dict[str, str], actions: Sequence[Action]) -> None:
        line = {
            "t": round(scene.t, 4),
            "hands": [hand_record(p) for p in scene.hands],
            "states": dict(states),
            "actions": [repr(a) for a in actions],
        }
        self._file.write(json.dumps(line) + "\n")

    def close(self) -> None:
        self._file.close()

    def __enter__(self) -> "Recorder":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
