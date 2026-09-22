"""Command-line entry point. Also used by the ``handcontrol-gui`` script under pythonw."""

from __future__ import annotations

import argparse
import logging
import logging.handlers
import os
import sys
from dataclasses import replace
from pathlib import Path

from handcontrol import __version__
from handcontrol.config import app_data_dir, load_settings


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="handcontrol", description="Control Windows with your hands.")
    parser.add_argument("--preview", action="store_true", help="show the debug preview window at start")
    parser.add_argument("--no-tray", action="store_true", help="run in the console without a tray icon (Ctrl+C quits)")
    parser.add_argument("--camera", type=int, default=None, metavar="N", help="camera index (overrides the config file)")
    parser.add_argument(
        "--config", type=Path, default=None, metavar="PATH",
        help="TOML config file (default: %%LOCALAPPDATA%%\\HandControl\\config.toml)",
    )
    parser.add_argument(
        "--record", type=Path, default=None, metavar="PATH",
        help="write what the pipeline sees every frame to this JSON Lines file (for tuning gestures)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    parser.add_argument("--version", action="version", version=f"handcontrol {__version__}")
    return parser.parse_args(argv)


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    if sys.stdout is None or sys.stderr is None:  # pythonw: no console, log to a rotating file
        log_dir = app_data_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = logging.handlers.RotatingFileHandler(
            log_dir / "handcontrol.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
    else:
        handler = logging.StreamHandler(sys.stderr)
    logging.basicConfig(level=level, format=fmt, handlers=[handler])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(args.verbose)
    os.environ.setdefault("GLOG_minloglevel", "2")  # quieten MediaPipe native logging
    settings = load_settings(args.config)
    if args.camera is not None:
        settings = replace(settings, camera=replace(settings.camera, index=args.camera))

    from handcontrol.app import App  # heavy imports (mediapipe, cv2) after logging is configured

    app = App(
        settings,
        model_path=app_data_dir() / "models" / "hand_landmarker.task",
        preview=args.preview,
        use_tray=not args.no_tray,
        record_path=args.record,
    )
    try:
        app.run()
    except KeyboardInterrupt:
        app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
