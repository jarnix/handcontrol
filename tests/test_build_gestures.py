from handbuilder import build_hand

from handcontrol.actions import OPEN_START_MENU, SHOW_DESKTOP, VOLUME_DOWN, VOLUME_UP, OpenUrl
from handcontrol.config import HandSettings, Settings, YoutubeSettings
from handcontrol.gestures import build_gestures
from handcontrol.gestures.base import GestureEngine
from handcontrol.hand import Finger, make_scene, pose_from_raw

H = HandSettings()
FPS = 30.0


def pose(**kwargs):
    return pose_from_raw(build_hand(**kwargs), 0.0, H)


def feed(engine, poses_per_frame, t0=0.0):
    actions = []
    for i, poses in enumerate(poses_per_frame):
        t = t0 + i / FPS
        actions.extend(engine.update(make_scene(poses, t), t))
    return actions


def test_registry_order_and_actions():
    gestures = build_gestures(Settings(youtube=YoutubeSettings(url="https://example.com")))
    assert [g.name for g in gestures] == ["start_menu", "scroll", "youtube", "show_desktop", "volume_up", "volume_down"]
    by_name = {g.name: g for g in gestures}
    assert by_name["start_menu"].action == OPEN_START_MENU
    assert by_name["youtube"].action == OpenUrl("https://example.com")
    assert by_name["show_desktop"].action == SHOW_DESKTOP
    assert by_name["volume_up"].action == VOLUME_UP
    assert by_name["volume_down"].action == VOLUME_DOWN


def test_end_to_end_bomb_opens_the_start_menu_once_and_silences_volume_while_the_hand_stays_open():
    s = Settings()
    engine = GestureEngine(build_gestures(s))
    closed, opened = pose(extended=set()), pose()
    bomb = [[closed]] * s.start_menu.fist_frames + [[opened]] * 3
    assert feed(engine, bomb) == [OPEN_START_MENU]
    # Hand left open and pointing up for a second: the bomb still owns the scene, no volume steps.
    assert feed(engine, [[opened]] * 30, t0=1.0) == []
    # Hand goes away, then an open hand pointing up engages the volume as usual.
    feed(engine, [[]], t0=2.0)
    assert feed(engine, [[opened]] * s.volume.engage_frames, t0=2.1) == [VOLUME_UP]


def test_end_to_end_rock_on_opens_youtube_once():
    s = Settings()
    engine = GestureEngine(build_gestures(s))
    rock = pose(extended={Finger.INDEX, Finger.PINKY})
    assert feed(engine, [[rock]] * (s.youtube.hold_frames + 10)) == [OpenUrl(s.youtube.url)]


def test_end_to_end_volume_repeats_while_held():
    s = Settings()
    engine = GestureEngine(build_gestures(s))
    up = pose(direction="up")
    frames = s.volume.engage_frames + 2 * s.volume.repeat_frames
    assert feed(engine, [[up]] * frames) == [VOLUME_UP, VOLUME_UP, VOLUME_UP]
