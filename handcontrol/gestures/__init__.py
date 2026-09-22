"""Gesture registry: the ordered list of gestures the app runs, built from settings."""

from __future__ import annotations

from handcontrol.actions import OPEN_START_MENU, SHOW_DESKTOP, VOLUME_DOWN, VOLUME_UP, OpenUrl
from handcontrol.config import Settings
from handcontrol.gestures.base import Gesture
from handcontrol.gestures.hold import HoldGesture
from handcontrol.gestures.poses import fist, middle_finger, open_hand, rock_on, volume_down, volume_up
from handcontrol.gestures.repeat import RepeatGesture
from handcontrol.gestures.transition import TransitionGesture
from handcontrol.gestures.two_finger_scroll import TwoFingerScroll


def build_gestures(s: Settings) -> list[Gesture]:
    """Priority order: an engaged gesture higher in the list owns the scene."""
    return [
        TransitionGesture("start_menu", fist, open_hand, OPEN_START_MENU,
                          s.start_menu.fist_frames, s.start_menu.open_within_frames, s.start_menu.cooldown_s),
        TwoFingerScroll(s.scroll),
        HoldGesture("youtube", rock_on, OpenUrl(s.youtube.url), s.youtube.hold_frames, s.youtube.cooldown_s),
        HoldGesture("show_desktop", middle_finger, SHOW_DESKTOP, s.show_desktop.hold_frames, s.show_desktop.cooldown_s),
        RepeatGesture("volume_up", volume_up, VOLUME_UP, s.volume.engage_frames, s.volume.repeat_frames),
        RepeatGesture("volume_down", volume_down, VOLUME_DOWN, s.volume.engage_frames, s.volume.repeat_frames),
    ]
