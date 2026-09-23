"""Application lifecycle: tray on the main thread, gesture pipeline on a worker thread."""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from handcontrol.actions import ActionExecutor
from handcontrol.camera import Camera
from handcontrol.config import Settings
from handcontrol.gestures import build_gestures
from handcontrol.gestures.base import GestureEngine
from handcontrol.hand import make_scene, pose_from_raw
from handcontrol.model import ensure_model
from handcontrol.preview import Preview
from handcontrol.recorder import Recorder
from handcontrol.tracker import HandTracker
from handcontrol.tray import State, Tray

log = logging.getLogger(__name__)

CAMERA_RETRY_S = 3.0


class App:
    def __init__(
        self,
        settings: Settings,
        model_path: Path,
        *,
        preview: bool = False,
        use_tray: bool = True,
        record_path: Path | None = None,
    ) -> None:
        self.settings = settings
        self.model_path = model_path
        self.preview_enabled = preview
        self.record_path = record_path
        self._stop = threading.Event()
        self._quit = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_state: tuple[str, str] | None = None
        self.tray: Tray | None = None
        if use_tray:
            self.tray = Tray(
                on_enabled_changed=self._on_enabled_changed,
                on_preview_changed=self._on_preview_changed,
                on_quit=self.quit,
                preview=preview,
            )

    # ----- lifecycle -------------------------------------------------------

    def run(self) -> None:
        """Block until quit. With a tray, the pipeline starts once the icon is visible."""
        if self.tray is not None:
            self.tray.run(ready=self.start_pipeline)
        else:
            self.start_pipeline()
            while not self._quit.wait(0.2):
                pass
        self.stop_pipeline()

    def quit(self) -> None:
        self._quit.set()
        self.stop_pipeline()
        if self.tray is not None:
            self.tray.stop()

    def start_pipeline(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._pipeline, name="pipeline", daemon=True)
        self._thread.start()

    def stop_pipeline(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None

    # ----- tray callbacks --------------------------------------------------

    def _on_enabled_changed(self, enabled: bool) -> None:
        if enabled:
            self.start_pipeline()
        else:
            self.stop_pipeline()
            self._set_state("disabled", "disabled (webcam off)")

    def _on_preview_changed(self, enabled: bool) -> None:
        self.preview_enabled = enabled

    def _set_state(self, state: State, text: str) -> None:
        if (state, text) == self._last_state:
            return
        self._last_state = (state, text)
        log.info("state: %s (%s)", state, text)
        if self.tray is not None:
            self.tray.set_state(state, text)

    def _notify(self, message: str) -> None:
        log.info(message)
        if self.tray is not None:
            self.tray.notify(message)

    # ----- pipeline thread -------------------------------------------------

    def _pipeline(self) -> None:
        try:
            if not self.model_path.exists():
                self._set_state("running", "downloading hand model")
                self._notify("Downloading the hand model (8 MB), one time only.")
            ensure_model(self.model_path)
        except OSError as exc:
            log.error("%s", exc)
            self._set_state("error", "model download failed, see log")
            return
        try:
            self._loop()
        except Exception:
            log.exception("pipeline crashed")
            self._set_state("error", "pipeline crashed, see log")

    def _loop(self) -> None:
        s = self.settings
        camera = Camera(s.camera.index, s.camera.width, s.camera.height)
        tracker = HandTracker(self.model_path, s.tracker, num_hands=2)
        engine = GestureEngine(build_gestures(s))
        from handcontrol import winput  # Windows-only module; imported here so tests never touch it

        executor = ActionExecutor(winput, wheel_step=s.scroll.wheel_step)
        preview = Preview()
        recorder = Recorder(self.record_path) if self.record_path is not None else None
        if recorder is not None:
            log.info("recording every frame to %s", self.record_path)
        log.info("gestures enabled: %s", ", ".join(engine.states) or "none")
        t0 = time.monotonic()
        try:
            while not self._stop.is_set():
                frame = camera.read()
                if frame is None:
                    engine.reset()
                    self._set_state("error", "camera unavailable, retrying")
                    self._stop.wait(CAMERA_RETRY_S)
                    continue
                self._set_state("running", "running")
                now = time.monotonic()
                try:
                    raws = tracker.detect(frame, int((now - t0) * 1000))
                except Exception:
                    log.exception("hand tracking failed on a frame")
                    continue
                scene = make_scene((pose_from_raw(raw, now, s.hand) for raw in raws), now)
                actions = engine.update(scene, now)
                for action in actions:
                    log.debug("action: %s", action)
                    executor.execute(action)
                if recorder is not None:
                    recorder.record(scene, engine.states, actions, raws)
                if self.preview_enabled:
                    preview.draw(frame, raws, scene, engine.states)
                elif preview.is_open:
                    preview.close()
        finally:
            if recorder is not None:
                recorder.close()
            preview.close()
            tracker.close()
            camera.release()
