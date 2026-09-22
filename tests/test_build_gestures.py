from handbuilder import build_hand

from handcontrol.actions import OPEN_START_MENU, SHOW_DESKTOP, VOLUME_DOWN, VOLUME_UP, OpenUrl
from handcontrol.config import HandSettings, Settings, YoutubeSettings
from handcontrol.gestures import build_gestures
from handcontrol.gestures.base import GestureEngine
from handcontrol.hand import Finger, make_scene, pose_from_raw

H = HandSettings()


def test_registry_order_and_actions():
    gestures = build_gestures(Settings(youtube=YoutubeSettings(url="https://example.com")))
    assert [g.name for g in gestures] == ["start_menu", "scroll", "youtube", "show_desktop", "volume_up", "volume_down"]
    by_name = {g.name: g for g in gestures}
    assert by_name["start_menu"].action == OPEN_START_MENU
    assert by_name["youtube"].action == OpenUrl("https://example.com")
    assert by_name["show_desktop"].action == SHOW_DESKTOP
    assert by_name["volume_up"].action == VOLUME_UP
    assert by_name["volume_down"].action == VOLUME_DOWN


def test_end_to_end_rock_on_opens_youtube_once():
    s = Settings()
    engine = GestureEngine(build_gestures(s))
    rock = pose_from_raw(build_hand(extended={Finger.INDEX, Finger.PINKY}), 0.0, H)
    actions = []
    for i in range(s.youtube.hold_frames + 10):
        actions.extend(engine.update(make_scene([rock], i / 30), i / 30))
    assert actions == [OpenUrl(s.youtube.url)]


def test_end_to_end_volume_repeats_while_held():
    s = Settings()
    engine = GestureEngine(build_gestures(s))
    up = pose_from_raw(build_hand(direction="up"), 0.0, H)
    actions = []
    for i in range(s.volume.engage_frames + 2 * s.volume.repeat_frames):
        actions.extend(engine.update(make_scene([up], i / 30), i / 30))
    assert actions == [VOLUME_UP, VOLUME_UP, VOLUME_UP]
