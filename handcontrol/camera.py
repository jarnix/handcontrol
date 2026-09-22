"""Webcam capture: lazy open, self-healing read, explicit release."""

from __future__ import annotations

import logging

import cv2
import numpy as np

log = logging.getLogger(__name__)


class Camera:
    def __init__(self, index: int, width: int, height: int) -> None:
        self.index = index
        self.width = width
        self.height = height
        self._cap: cv2.VideoCapture | None = None

    @property
    def is_open(self) -> bool:
        return self._cap is not None

    def open(self) -> bool:
        cap = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            log.warning("camera %d could not be opened", self.index)
            return False
        # MJPG lets DirectShow deliver 30 fps at 720p; raw YUY2 often drops to 5-10 fps.
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._cap = cap
        log.info(
            "camera %d open at %dx%d",
            self.index,
            int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )
        return True

    def read(self) -> np.ndarray | None:
        """Return a BGR frame, or None if the camera is unavailable (it will retry on the next call)."""
        if self._cap is None and not self.open():
            return None
        assert self._cap is not None
        ok, frame = self._cap.read()
        if not ok or frame is None:
            log.warning("camera %d read failed, releasing", self.index)
            self.release()
            return None
        return frame

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
