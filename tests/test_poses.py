from handbuilder import build_hand

from handcontrol.config import HandSettings
from handcontrol.gestures.poses import clap, middle_finger, rock_on, volume_down, volume_up
from handcontrol.hand import Finger, make_scene, pose_from_raw

H = HandSettings()
WIDTH = 0.06 * 1.25  # builder knuckle width at the default scale

ROCK = {Finger.INDEX, Finger.PINKY}
MIDDLE = {Finger.MIDDLE}


def pose(**kwargs):
    return pose_from_raw(build_hand(**kwargs), 0.0, H)


def scene(*poses):
    return make_scene(poses, 0.0)


def side_by_side(widths_apart, second=None, **both):
    """Two hands in the same orientation, the second one ``widths_apart`` hand widths to the right."""
    second = {**both, **(second or {})}
    return scene(pose(center=(0.4, 0.5), **both), pose(center=(0.4 + widths_apart * WIDTH, 0.5), **second))


def test_clap_two_open_hands_close_together():
    assert clap(1.2)(side_by_side(0.5))


def test_clap_rejects_hands_far_apart():
    assert not clap(1.2)(side_by_side(3.0))


def test_clap_threshold_is_configurable():
    assert not clap(1.2)(side_by_side(2.0))
    assert clap(2.5)(side_by_side(2.0))


def test_clap_rejects_a_closed_hand():
    assert not clap(1.2)(side_by_side(0.5, second={"extended": set()}))
    assert not clap(1.2)(side_by_side(0.5, second={"extended": {Finger.INDEX, Finger.MIDDLE}}))


def test_clap_works_in_any_orientation():
    assert clap(1.2)(side_by_side(0.5, direction="camera"))
    assert clap(1.2)(side_by_side(0.5, direction="down"))


def test_clap_needs_two_hands():
    assert not clap(1.2)(scene(pose()))
    assert not clap(1.2)(scene())


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
    assert not any(p(empty) for p in (clap(1.2), rock_on, middle_finger, volume_up, volume_down))
