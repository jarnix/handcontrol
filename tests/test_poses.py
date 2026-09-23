from handbuilder import build_hand

from handcontrol.config import HandSettings
from handcontrol.gestures.poses import fist, middle_finger, open_hand, rock_on, volume_down, volume_up
from handcontrol.hand import Finger, make_scene, pose_from_raw

H = HandSettings()

ROCK = {Finger.INDEX, Finger.PINKY}
MIDDLE = {Finger.MIDDLE}


def pose(**kwargs):
    return pose_from_raw(build_hand(**kwargs), 0.0, H)


def scene(*poses):
    return make_scene(poses, 0.0)


def test_fist_and_open_hand_use_the_larger_hand_in_any_orientation():
    for direction in ("up", "down", "camera", "side"):
        assert fist(scene(pose(extended=set(), direction=direction)))
        assert open_hand(scene(pose(direction=direction)))
    assert fist(scene(pose(extended=set(), scale=2.0), pose(scale=1.0)))          # fist is primary
    assert not fist(scene(pose(extended=set(), scale=1.0), pose(scale=2.0)))      # open hand is primary
    assert open_hand(scene(pose(scale=2.0), pose(extended=set(), scale=1.0)))
    assert not open_hand(scene(pose(extended=set())))


def test_rock_on_uses_the_larger_hand():
    assert rock_on(scene(pose(extended=ROCK)))
    assert rock_on(scene(pose(extended=ROCK, scale=2.0), pose(scale=1.0)))       # rock-on hand is primary
    assert not rock_on(scene(pose(extended=ROCK, scale=1.0), pose(scale=2.0)))   # open hand is primary
    assert not rock_on(scene(pose()))


def test_middle_finger_uses_the_larger_hand():
    assert middle_finger(scene(pose(extended=MIDDLE)))
    assert middle_finger(scene(pose(extended=MIDDLE, scale=2.0), pose(scale=1.0)))
    assert not middle_finger(scene(pose(extended=MIDDLE, scale=1.0), pose(scale=2.0)))
    assert not middle_finger(scene(pose(extended=ROCK)))


def test_volume_up_needs_exactly_one_open_hand_pointing_up():
    up = pose(direction="up")
    assert volume_up(scene(up))
    assert not volume_down(scene(up))
    assert not volume_up(scene(up, pose(center=(0.9, 0.5))))                   # second hand visible
    assert not volume_up(scene(pose(direction="camera")))                       # foreshortened
    assert not volume_up(scene(pose(direction="side")))
    assert not volume_up(scene(pose(extended={Finger.INDEX, Finger.MIDDLE})))  # not an open hand


def test_volume_down_mirrors_volume_up():
    down = pose(direction="down")
    assert volume_down(scene(down))
    assert not volume_up(scene(down))
    assert not volume_down(scene(down, pose(center=(0.9, 0.5), direction="down")))


def test_empty_scene_matches_nothing():
    empty = scene()
    assert not any(p(empty) for p in (fist, open_hand, rock_on, middle_finger, volume_up, volume_down))
