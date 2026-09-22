from handcontrol.actions import VK_LWIN, ActionExecutor, OpenStartMenu, Scroll


class FakeBackend:
    def __init__(self, cursor=(10, 10), rect=(0, 0, 100, 100)):
        self.cursor = cursor
        self.rect = rect
        self.calls = []

    def tap_key(self, vk):
        self.calls.append(("tap_key", vk))

    def scroll_wheel(self, delta):
        self.calls.append(("scroll_wheel", delta))

    def cursor_pos(self):
        return self.cursor

    def set_cursor_pos(self, x, y):
        self.cursor = (x, y)
        self.calls.append(("set_cursor_pos", x, y))

    def foreground_window_rect(self):
        return self.rect


def test_start_menu_taps_the_windows_key():
    b = FakeBackend()
    ActionExecutor(b).execute(OpenStartMenu())
    assert b.calls == [("tap_key", VK_LWIN)]
    assert VK_LWIN == 0x5B


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
