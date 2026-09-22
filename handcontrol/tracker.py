"""MediaPipe HandLandmarker wrapper (Tasks API, VIDEO mode, synchronous, CPU)."""

from __future__ import annotations

from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

from handcontrol.config import TrackerSettings
from handcontrol.hand import RawHand


class HandTracker:
    def __init__(self, model_path: Path, settings: TrackerSettings, num_hands: int = 2) -> None:
        options = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=settings.min_hand_detection_confidence,
            min_hand_presence_confidence=settings.min_hand_presence_confidence,
            min_tracking_confidence=settings.min_tracking_confidence,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        self._last_timestamp_ms = -1

    def detect(self, frame_bgr: np.ndarray, timestamp_ms: int) -> list[RawHand]:
        # VIDEO mode requires strictly increasing timestamps.
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1
        self._last_timestamp_ms = timestamp_ms
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(image, timestamp_ms)
        return [
            RawHand(
                landmarks=[(p.x, p.y, p.z) for p in landmarks],
                world=[(p.x, p.y, p.z) for p in world],
                handedness=categories[0].category_name,
                score=categories[0].score,
            )
            for landmarks, world, categories in zip(
                result.hand_landmarks, result.hand_world_landmarks, result.handedness
            )
        ]

    def close(self) -> None:
        self._landmarker.close()
