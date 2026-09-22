from handcontrol.tray import make_icon


def test_icons_are_square_rgba_and_coloured_by_state():
    running, disabled, error = (make_icon(s) for s in ("running", "disabled", "error"))
    for img in (running, disabled, error):
        assert img.size == (64, 64) and img.mode == "RGBA"
        assert img.getpixel((0, 0))[3] == 0            # corner outside the disc is transparent
        assert img.getpixel((4, 32))[3] == 255         # left edge of the disc is painted
    assert len({running.getpixel((4, 32)), disabled.getpixel((4, 32)), error.getpixel((4, 32))}) == 3
