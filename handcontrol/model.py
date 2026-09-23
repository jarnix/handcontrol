"""Locate or download the MediaPipe hand landmarker model."""

from __future__ import annotations

import logging
import os
import urllib.request
from pathlib import Path
from typing import Callable

log = logging.getLogger(__name__)

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"

Fetch = Callable[[str, str], object]


def _download(url: str, dest: str) -> None:
    urllib.request.urlretrieve(url, dest)


def ensure_model(path: Path, fetch: Fetch = _download) -> Path:
    """Return ``path``, downloading the model there first if it is missing.

    Downloads to a ``.part`` file and renames on success so a failed download
    never leaves a truncated model behind. Raises OSError on any failure.
    """
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".part")
    log.info("downloading hand model to %s", path)
    try:
        fetch(MODEL_URL, str(part))
        os.replace(part, path)
    except Exception as exc:
        part.unlink(missing_ok=True)
        raise OSError(f"model download failed: {exc}") from exc
    return path
