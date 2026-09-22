"""Guided, labelled recording of hand poses for tuning the finger classifier.

Shows each instruction on the preview window with a countdown, records raw
landmarks under that label, then prints how candidate "finger extended"
classifiers behave for every labelled pose:

  angle3d  world-landmark bend angle at the middle joint (180 = straight)
  ratio2d  image distance wrist->tip divided by wrist->PIP (> 1 = tip beyond the knuckle)
  ratio3d  the same ratio on world landmarks

usage: uv run python tools/record_poses.py C:/tmp/poses.jsonl [--camera N]
"""

from __future__ import annotations

import argparse
import json
import math
import time
from collections import defaultdict
from pathlib import Path

import cv2

from handcontrol.camera import Camera
from handcontrol.config import HandSettings, Settings, app_data_dir
from handcontrol.hand import FINGER_JOINTS, WRIST, Finger, RawHand, angle_deg, pose_from_raw
from handcontrol.model import ensure_model
from handcontrol.preview import CONNECTIONS, GREEN, WHITE, YELLOW
from handcontrol.recorder import hand_record
from handcontrol.tracker import HandTracker

STEPS = [
    ("open_up_palm", "OPEN hand, fingers UP, PALM to camera", 6.0),
    ("open_up_back", "OPEN hand, fingers UP, BACK of hand to camera", 6.0),
    ("open_down", "OPEN hand, fingers DOWN, hand in front of your chest", 6.0),
    ("fist", "FIST, in front of your chest", 6.0),
    ("relaxed", "Relaxed half-open hand, as when resting", 5.0),
]
READY_S = 5.0
GUIDE = (0.2, 0.15, 0.8, 0.9)  # keep the hand inside this box (fractions of the frame)
WINDOW = "HandControl pose recording"
FINGERS = (Finger.THUMB, Finger.INDEX, Finger.MIDDLE, Finger.RING, Finger.PINKY)


def ratio(points, finger) -> float:
    root, joint, tip = FINGER_JOINTS[finger]
    w = points[WRIST]
    d_pip = math.dist(w, points[joint])
    return math.dist(w, points[tip]) / d_pip if d_pip > 0 else 0.0


def classifiers(raw: RawHand) -> dict[str, dict[str, float]]:
    xy = [(x, y) for x, y, _ in raw.landmarks]
    return {
        "angle3d": {f.value: angle_deg(*(raw.world[i] for i in FINGER_JOINTS[f])) for f in FINGERS},
        "ratio2d": {f.value: ratio(xy, f) for f in FINGERS},
        "ratio3d": {f.value: ratio(raw.world, f) for f in FINGERS},
    }


def draw(frame, raws, poses, headline, sub):
    img = annotated(frame, raws)
    h, w = img.shape[:2]
    x0, y0, x1, y1 = GUIDE
    cv2.rectangle(img, (int(x0 * w), int(y0 * h)), (int(x1 * w), int(y1 * h)), (255, 200, 0), 2)
    cv2.putText(img, "keep the hand inside the box", (int(x0 * w) + 8, int(y1 * h) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 200, 0), 2, cv2.LINE_AA)
    cv2.rectangle(img, (0, 0), (w, 110), (0, 0, 0), -1)
    cv2.putText(img, headline, (20, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.1, YELLOW, 3, cv2.LINE_AA)
    cv2.putText(img, sub, (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.9, WHITE, 2, cv2.LINE_AA)
    y = 150
    for pose in poses:
        flags = " ".join(f.value[:2] + ("+" if on else "-") for f, on in pose.fingers.items())
        angles = " ".join(f"{f.value[:2]}{a:3.0f}" for f, a in pose.finger_angles.items())
        cv2.putText(img, f"{flags}  pointing={pose.pointing}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, YELLOW, 2, cv2.LINE_AA)
        cv2.putText(img, f"angles {angles}", (20, y + 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, YELLOW, 2, cv2.LINE_AA)
        y += 60
    cv2.imshow(WINDOW, img)
    cv2.waitKey(1)


def annotated(frame, raws):
    """Mirrored copy of the frame with every detected hand's landmarks drawn."""
    img = frame.copy()
    h, w = img.shape[:2]
    for raw in raws:
        pts = [(int(x * w), int(y * h)) for x, y, _ in raw.landmarks]
        for a, b in CONNECTIONS:
            cv2.line(img, pts[a], pts[b], GREEN, 2)
        for p in pts:
            cv2.circle(img, p, 4, WHITE, -1)
    return cv2.flip(img, 1)


def summarise(records: list[dict]) -> None:
    by_label = defaultdict(list)
    for r in records:
        if r["phase"] == "record":
            by_label[r["label"]].append(r)
    print()
    print("label          frames detected  pointing(up/down/none)   per finger: median angle3d | ratio2d | ratio3d   (thumb index middle ring pinky)")
    for label, rows in by_label.items():
        hands = [r for r in rows if r["raw"]]
        if not hands:
            print(f"{label:14} {len(rows):6d} {0:8d}")
            continue
        pointing = defaultdict(int)
        stats = {name: defaultdict(list) for name in ("angle3d", "ratio2d", "ratio3d")}
        for r in hands:
            raw = RawHand(landmarks=[tuple(p) for p in r["raw"][0]["landmarks"]], world=[tuple(p) for p in r["raw"][0]["world"]],
                          handedness=r["raw"][0]["handedness"], score=r["raw"][0]["score"])
            pointing[str(r["hands"][0]["pointing"])] += 1
            for name, per_finger in classifiers(raw).items():
                for finger, value in per_finger.items():
                    stats[name][finger].append(value)
        med = lambda values: sorted(values)[len(values) // 2]
        cells = []
        for f in FINGERS:
            cells.append(f"{med(stats['angle3d'][f.value]):3.0f}|{med(stats['ratio2d'][f.value]):.2f}|{med(stats['ratio3d'][f.value]):.2f}")
        p = f"{pointing.get('up', 0)}/{pointing.get('down', 0)}/{pointing.get('None', 0)}"
        print(f"{label:14} {len(rows):6d} {len(hands):8d}  {p:22}  " + "  ".join(cells))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--camera", type=int, default=None)
    args = parser.parse_args()
    settings = Settings()
    camera_index = settings.camera.index if args.camera is None else args.camera
    model = ensure_model(app_data_dir() / "models" / "hand_landmarker.task")
    camera = Camera(camera_index, settings.camera.width, settings.camera.height)
    tracker = HandTracker(model, settings.tracker, num_hands=2)
    hand_settings = HandSettings()
    records: list[dict] = []
    snapshots = args.output.with_suffix("").with_name(args.output.stem + "_frames")
    snapshots.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    try:
        for label, text, seconds in STEPS:
            for phase, duration in (("ready", READY_S), ("record", seconds)):
                phase_start = time.monotonic()
                last_snapshot = -1.0
                while True:
                    now = time.monotonic()
                    left = duration - (now - phase_start)
                    if left <= 0:
                        break
                    frame = camera.read()
                    if frame is None:
                        time.sleep(0.05)
                        continue
                    raws = tracker.detect(frame, int((now - t0) * 1000))
                    poses = [pose_from_raw(r, now, hand_settings) for r in raws]
                    headline = ("NEXT, get ready: " if phase == "ready" else "HOLD NOW: ") + text
                    sub = f"{left:3.0f} s   step {STEPS.index((label, text, seconds)) + 1}/{len(STEPS)}   {'RECORDING' if phase == 'record' else 'not recording yet'}"
                    draw(frame, raws, poses, headline, sub)
                    if phase == "record" and now - last_snapshot >= 1.5:  # a few small pictures per step, to look at afterwards
                        last_snapshot = now
                        small = cv2.resize(annotated(frame, raws), (640, 360))
                        cv2.imwrite(str(snapshots / f"{label}_{now - phase_start:04.1f}s_{len(raws)}hands.jpg"), small, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    records.append({
                        "t": round(now - t0, 4),
                        "label": label,
                        "phase": phase,
                        "raw": [{"landmarks": [[round(v, 4) for v in p] for p in r.landmarks],
                                 "world": [[round(v, 4) for v in p] for p in r.world],
                                 "handedness": r.handedness, "score": round(r.score, 3)} for r in raws],
                        "hands": [hand_record(p) for p in poses],
                    })
    finally:
        cv2.destroyAllWindows()
        tracker.close()
        camera.release()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    print(f"wrote {len(records)} frames to {args.output}")
    summarise(records)


if __name__ == "__main__":
    main()
