import pytest
from handbuilder import build_hand

from handcontrol.config import HandSettings
from handcontrol.hand import Finger, angle_deg, make_scene, pose_from_raw

SETTINGS = HandSettings()
WIDTH = 0.06 * 1.25  # builder knuckle width in image units at the default scale


def pose(**kwargs):
    return pose_from_raw(build_hand(**kwargs), t=0.0, settings=SETTINGS)


def test_angle_straight_and_right_angle():
    assert angle_deg((0, 0, 0), (0, 1, 0), (0, 2, 0)) == pytest.approx(180.0)
    assert angle_deg((1, 0, 0), (0, 0, 0), (0, 1, 0)) == pytest.approx(90.0)


def test_degenerate_angle_is_zero():
    assert angle_deg((0, 0, 0), (0, 0, 0), (1, 0, 0)) == 0.0


def test_open_hand():
    p = pose()
    assert all(p.fingers.values())
    assert p.is_open_hand
    assert not (p.is_two_finger or p.is_rock_on or p.is_middle_finger)


def test_fist():
    p = pose(extended=set())
    assert not any(p.fingers.values())
    assert p.is_fist
    assert not (p.is_open_hand or p.is_two_finger or p.is_rock_on or p.is_middle_finger)


def test_fist_ignores_the_thumb_and_needs_every_finger_curled():
    assert pose(extended={Finger.THUMB}).is_fist
    assert not pose(extended={Finger.INDEX}).is_fist
    assert not pose().is_fist


def test_two_finger_pose():
    p = pose(extended={Finger.INDEX, Finger.MIDDLE})
    assert p.two_fingers_joined and p.is_two_finger
    assert not (p.is_open_hand or p.is_rock_on or p.is_middle_finger)
    assert pose(extended={Finger.THUMB, Finger.INDEX, Finger.MIDDLE}).is_two_finger


def test_spread_fingers_are_not_joined():
    p = pose(extended={Finger.INDEX, Finger.MIDDLE}, spread=True)
    assert not p.two_fingers_joined and not p.is_two_finger


def test_rock_on():
    p = pose(extended={Finger.INDEX, Finger.PINKY})
    assert p.is_rock_on
    assert not (p.is_open_hand or p.is_two_finger or p.is_middle_finger)
    assert pose(extended={Finger.THUMB, Finger.INDEX, Finger.PINKY}).is_rock_on


def test_middle_finger():
    p = pose(extended={Finger.MIDDLE})
    assert p.is_middle_finger
    assert not (p.is_open_hand or p.is_two_finger or p.is_rock_on)
    assert pose(extended={Finger.THUMB, Finger.MIDDLE}).is_middle_finger


def test_index_alone_matches_no_pose():
    p = pose(extended={Finger.INDEX})
    assert not (p.is_open_hand or p.is_two_finger or p.is_rock_on or p.is_middle_finger)


def test_open_hand_ignores_thumb():
    assert pose(extended={Finger.INDEX, Finger.MIDDLE, Finger.RING, Finger.PINKY}).is_open_hand


def test_pointing_up_and_down():
    up, down = pose(direction="up"), pose(direction="down")
    assert up.pointing == "up" and up.direction_deg == pytest.approx(0.0, abs=1e-6)
    assert down.pointing == "down" and abs(down.direction_deg) == pytest.approx(180.0)
    assert up.direction_len == pytest.approx(0.08 / 0.06)


def test_sideways_and_foreshortened_hands_point_nowhere():
    side, camera = pose(direction="side"), pose(direction="camera")
    assert side.pointing is None and side.direction_deg == pytest.approx(90.0)
    assert camera.pointing is None and camera.direction_len < 0.1


@pytest.mark.parametrize("direction", ["up", "down", "camera", "side"])
def test_finger_flags_hold_in_every_direction(direction):
    assert pose(extended={Finger.INDEX, Finger.PINKY}, direction=direction).is_rock_on
    assert pose(direction=direction).is_open_hand
    assert not pose(extended=set(), direction=direction).is_open_hand


@pytest.mark.parametrize("direction", ["up", "down", "camera", "side"])
def test_hand_width_is_orientation_invariant(direction):
    assert pose(direction=direction).hand_width == pytest.approx(WIDTH)
    assert pose(direction=direction, center=(0.2, 0.8)).hand_width == pytest.approx(WIDTH)
    assert pose(direction=direction, scale=2.0).hand_width == pytest.approx(0.12)


def test_points_follow_the_hand():
    a, b = pose(center=(0.5, 0.5)), pose(center=(0.5, 0.3))
    assert a.palm_center[1] - b.palm_center[1] == pytest.approx(0.2)
    assert a.two_finger_point[1] - b.two_finger_point[1] == pytest.approx(0.2)


def test_scene_orders_by_width_and_exposes_primary_single_pair():
    small, big = pose(scale=1.0), pose(scale=2.0)
    both = make_scene([small, big], 1.0)
    assert both.primary is big and both.pair == (big, small) and both.single is None and both.t == 1.0
    one = make_scene([small], 2.0)
    assert one.primary is small and one.single is small and one.pair is None
    none = make_scene([], 3.0)
    assert none.primary is None and none.single is None and none.pair is None and none.hands == ()


def test_pose_carries_timestamp():
    assert pose_from_raw(build_hand(), t=12.5, settings=SETTINGS).t == 12.5
