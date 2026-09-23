from handcontrol.actions import (
    OPEN_START_MENU,
    SHOW_DESKTOP,
    VK_D,
    VK_LWIN,
    VK_VOLUME_DOWN,
    VK_VOLUME_UP,
    VOLUME_DOWN,
    VOLUME_UP,
    ActionExecutor,
    OpenUrl,
    Scroll,
    TapKeys,
)


class FakeBackend:
    def __init__(self, cursor=(10, 10), rect=(0, 0, 100, 100)):
        self.cursor = cursor
        self.rect = rect
        self.calls = []

    def tap_keys(self, vks):
        self.calls.append(("tap_keys", tuple(vks)))

    def scroll_wheel(self, delta):
        self.calls.append(("scroll_wheel", delta))

    def cursor_pos(self):
        return self.cursor

    def set_cursor_pos(self, x, y):
        self.cursor = (x, y)
        self.calls.append(("set_cursor_pos", x, y))

    def foreground_window_rect(self):
        return self.rect

    def open_url(self, url):
        self.calls.append(("open_url", url))


def test_key_constants():
    assert (VK_LWIN, VK_D, VK_VOLUME_UP, VK_VOLUME_DOWN) == (0x5B, 0x44, 0xAF, 0xAE)
    assert OPEN_START_MENU == TapKeys((VK_LWIN,))
    assert SHOW_DESKTOP == TapKeys((VK_LWIN, VK_D))
    assert VOLUME_UP == TapKeys((VK_VOLUME_UP,))
    assert VOLUME_DOWN == TapKeys((VK_VOLUME_DOWN,))


def test_tap_keys_passes_the_chord_through():
    b = FakeBackend()
    ActionExecutor(b).execute(SHOW_DESKTOP)
    assert b.calls == [("tap_keys", (VK_LWIN, VK_D))]


def test_open_url_goes_to_the_backend():
    b = FakeBackend()
    ActionExecutor(b).execute(OpenUrl("https://www.youtube.com"))
    assert b.calls == [("open_url", "https://www.youtube.com")]


def test_scroll_inside_foreground_window_only_sends_wheel():
    b = FakeBackend(cursor=(50, 50))
    ActionExecutor(b).execute(Scroll(2))
    assert b.calls == [("scroll_wheel", 240)]


def test_scroll_moves_cursor_into_foreground_window_first():
    b = FakeBackend(cursor=(500, 500), rect=(100, 200, 300, 400))
    ActionExecutor(b).execute(Scroll(-1))
    assert b.calls == [("set_cursor_pos", 200, 300), ("scroll_wheel", -120)]


def test_cursor_on_the_window_edge_counts_as_inside():
    b = FakeBackend(cursor=(0, 0))
    ActionExecutor(b).execute(Scroll(1))
    assert b.calls == [("scroll_wheel", 120)]


def test_no_foreground_window_scrolls_without_moving():
    b = FakeBackend(cursor=(500, 500), rect=None)
    ActionExecutor(b).execute(Scroll(1))
    assert b.calls == [("scroll_wheel", 120)]


def test_wheel_step_is_configurable():
    b = FakeBackend()
    ActionExecutor(b, wheel_step=40).execute(Scroll(3))
    assert b.calls == [("scroll_wheel", 120)]
