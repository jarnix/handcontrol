from handcontrol.actions import OPEN_START_MENU
from handcontrol.gestures.transition import TransitionGesture
from handcontrol.hand import Scene

ACTION = OPEN_START_MENU
SCENE = Scene(hands=(), t=0.0)  # the fake predicates ignore the scene
FPS = 30.0


def make(min_start_frames=3, max_transition_frames=4, cooldown_s=1.0):
    state = {"pose": "none"}
    gesture = TransitionGesture(
        "g",
        start=lambda scene: state["pose"] == "start",
        end=lambda scene: state["pose"] == "end",
        action=ACTION,
        min_start_frames=min_start_frames,
        max_transition_frames=max_transition_frames,
        cooldown_s=cooldown_s,
    )
    return gesture, state


POSES = {"S": "start", "E": "end", "O": "other", "N": "none"}


def run(gesture, state, pattern, t0=0.0):
    """Feed a string of S(tart)/E(nd)/O(ther)/N(one) frames at 30 fps; return actions per frame."""
    out = []
    for i, ch in enumerate(pattern):
        state["pose"] = POSES[ch]
        out.append(gesture.update(SCENE, t0 + i / FPS))
    return out


def fires(per_frame):
    return sum(len(a) for a in per_frame)


def test_fires_when_the_end_pose_follows_a_held_start_pose():
    g, st = make()
    assert run(g, st, "SSSE") == [[], [], [], [ACTION]]
    assert g.state == "RELEASE" and g.engaged


def test_start_pose_must_be_held_long_enough():
    g, st = make()
    assert fires(run(g, st, "SSE")) == 0
    assert fires(run(g, st, "SSSE", t0=1.0)) == 1


def test_a_few_in_between_frames_are_allowed():
    g, st = make(max_transition_frames=4)
    assert fires(run(g, st, "SSSOOE")) == 1


def test_too_many_in_between_frames_disarm():
    g, st = make(max_transition_frames=4)
    assert fires(run(g, st, "SSSOOOOOE")) == 0
    assert g.state == "IDLE"


def test_returning_to_the_start_pose_restarts_the_transition_window():
    g, st = make(max_transition_frames=3)
    assert fires(run(g, st, "SSSOOOSOOOE")) == 1


def test_end_pose_alone_does_nothing():
    g, st = make()
    assert fires(run(g, st, "EEEEE")) == 0
    assert not g.engaged


def test_holding_the_end_pose_keeps_ownership_without_refiring():
    g, st = make()
    assert fires(run(g, st, "SSSE" + "E" * 30)) == 1
    assert g.state == "RELEASE" and g.engaged


def test_refire_needs_release_cooldown_and_a_new_start():
    g, st = make(cooldown_s=1.0)
    assert fires(run(g, st, "SSSE")) == 1                    # fires at t = 0.1
    assert fires(run(g, st, "N" + "SSSE", t0=0.2)) == 0      # released, but inside the cooldown
    assert g.state == "COOLDOWN" and not g.engaged
    assert fires(run(g, st, "SSSE", t0=2.0)) == 1


def test_release_after_the_cooldown_expired_rearms_immediately():
    g, st = make(cooldown_s=1.0)
    run(g, st, "SSSE")
    run(g, st, "E" * 40, t0=0.2)                             # end pose held past the cooldown
    assert fires(run(g, st, "N" + "SSSE", t0=2.0)) == 1


def test_engaged_while_armed_or_waiting_for_release():
    g, st = make()
    assert not g.engaged and g.state == "IDLE"
    run(g, st, "SS")
    assert not g.engaged
    run(g, st, "S", t0=0.1)
    assert g.engaged and g.state == "ARMED"
    run(g, st, "E", t0=0.2)
    assert g.engaged and g.state == "RELEASE"
    run(g, st, "N", t0=0.3)
    assert not g.engaged and g.state == "COOLDOWN"


def test_reset_clears_an_armed_gesture():
    g, st = make()
    run(g, st, "SSS")
    g.reset()
    assert g.state == "IDLE" and not g.engaged
    assert fires(run(g, st, "E", t0=1.0)) == 0
