"""System tray icon and menu (pystray). Runs on the main thread."""

from __future__ import annotations

import logging
from typing import Callable, Literal

import pystray
from PIL import Image, ImageDraw

log = logging.getLogger(__name__)

State = Literal["running", "disabled", "error"]

_COLORS: dict[str, tuple[int, int, int, int]] = {
    "running": (46, 160, 67, 255),
    "disabled": (128, 128, 128, 255),
    "error": (220, 53, 69, 255),
}


def make_icon(state: State, size: int = 64) -> Image.Image:
    """A coloured disc with a simple white hand glyph."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((0, 0, size - 1, size - 1), fill=_COLORS[state])
    u = size / 16
    d.rounded_rectangle((5 * u, 7 * u, 11 * u, 13 * u), radius=u, fill="white")  # palm
    for i in range(4):  # four fingers
        x = (5 + 1.5 * i) * u
        d.rounded_rectangle((x, 3 * u, x + u, 8 * u), radius=u / 2, fill="white")
    d.rounded_rectangle((3 * u, 7 * u, 5.5 * u, 8.5 * u), radius=u / 2, fill="white")  # thumb
    return img


class Tray:
    def __init__(
        self,
        *,
        on_enabled_changed: Callable[[bool], None],
        on_preview_changed: Callable[[bool], None],
        on_quit: Callable[[], None],
        preview: bool = False,
    ) -> None:
        self._enabled = True
        self._preview = preview
        self._on_enabled_changed = on_enabled_changed
        self._on_preview_changed = on_preview_changed
        self._on_quit = on_quit
        self._icon = pystray.Icon(
            "handcontrol",
            icon=make_icon("running"),
            title="HandControl - starting",
            menu=pystray.Menu(
                pystray.MenuItem("Enabled", self._toggle_enabled, checked=lambda item: self._enabled),
                pystray.MenuItem("Show preview", self._toggle_preview, checked=lambda item: self._preview),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", self._quit),
            ),
        )

    def _toggle_enabled(self, icon, item) -> None:
        self._enabled = not self._enabled
        self._on_enabled_changed(self._enabled)

    def _toggle_preview(self, icon, item) -> None:
        self._preview = not self._preview
        self._on_preview_changed(self._preview)

    def _quit(self, icon, item) -> None:
        self._on_quit()

    def set_state(self, state: State, text: str) -> None:
        self._icon.icon = make_icon(state)
        self._icon.title = f"HandControl - {text}"

    def notify(self, message: str) -> None:
        try:
            self._icon.notify(message, "HandControl")
        except Exception:  # notifications are best-effort
            log.debug("tray notification failed", exc_info=True)

    def run(self, ready: Callable[[], None]) -> None:
        """Block running the tray loop; ``ready`` is called once the icon is visible."""

        def setup(icon: pystray.Icon) -> None:
            icon.visible = True
            ready()

        self._icon.run(setup=setup)

    def stop(self) -> None:
        self._icon.stop()
