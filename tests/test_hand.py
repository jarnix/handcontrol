import pytest
from handbuilder import build_hand

from handcontrol.config import HandSettings
from handcontrol.hand import Finger, angle_deg, pose_from_raw

SETTINGS = HandSettings()


def pose(**kwargs):
    return pose_from_raw(build_hand(**kwargs), t=0.0, settings=SETTINGS)


def test_angle_straight_and_right_angle():
    assert angle_deg((0, 0, 0), (0, 1, 0), (0, 2, 0)) == pytest.approx(180.0)
    assert angle_deg((1, 0, 0), (0, 0, 0), (0, 1, 0)) == pytest.approx(90.0)


def test_degenerate_angle_is_zero():
    assert angle_deg((0, 0, 0), (0, 0, 0), (1, 0, 0)) == 0.0


def test_open_palm_has_all_fingers_extended():
    p = pose()
    assert all(p.fingers.values())
    assert p.palm_facing_camera
    assert p.is_open_palm
    assert not p.is_two_finger


def test_fist_has_nothing_extended():
    p = pose(extended=set())
    assert not any(p.fingers.values())
    assert not p.is_open_palm
    assert not p.is_two_finger


def test_two_finger_pose():
    p = pose(extended={Finger.INDEX, Finger.MIDDLE})
    assert p.two_fingers_joined
    assert p.is_two_finger
    assert not p.is_open_palm


def test_two_finger_pose_ignores_thumb():
    assert pose(extended={Finger.THUMB, Finger.INDEX, Finger.MIDDLE}).is_two_finger


def test_spread_fingers_are_not_joined():
    p = pose(extended={Finger.INDEX, Finger.MIDDLE}, spread=True)
    assert not p.two_fingers_joined
    assert not p.is_two_finger


def test_open_palm_requires_palm_facing_camera():
    p = pose(facing=False)
    assert not p.palm_facing_camera
    assert not p.is_open_palm


def test_open_palm_ignores_thumb():
    assert pose(extended={Finger.INDEX, Finger.MIDDLE, Finger.RING, Finger.PINKY}).is_open_palm


@pytest.mark.parametrize("handedness", ["Left", "Right"])
def test_facing_rule_holds_for_both_hands(handedness):
    assert pose(handedness=handedness, facing=True).palm_facing_camera
    assert not pose(handedness=handedness, facing=False).palm_facing_camera


def test_palm_size_is_distance_invariant_and_points_follow_the_hand():
    a = pose(center=(0.5, 0.5))
    b = pose(center=(0.5, 0.3))
    assert a.palm_size == pytest.approx(0.1)
    assert b.palm_size == pytest.approx(0.1)
    assert a.palm_center[1] - b.palm_center[1] == pytest.approx(0.2)
    assert a.two_finger_point[1] - b.two_finger_point[1] == pytest.approx(0.2)


def test_pose_carries_timestamp():
    assert pose_from_raw(build_hand(), t=12.5, settings=SETTINGS).t == 12.5
