import json

from handbuilder import build_hand

from handcontrol.actions import VOLUME_UP
from handcontrol.config import HandSettings
from handcontrol.hand import Finger, make_scene, pose_from_raw
from handcontrol.recorder import Recorder


def test_writes_one_json_line_per_frame(tmp_path):
    path = tmp_path / "session.jsonl"
    up = pose_from_raw(build_hand(direction="up"), 1.0, HandSettings())
    rock = pose_from_raw(build_hand(extended={Finger.INDEX, Finger.PINKY}, scale=1.0), 1.0, HandSettings())
    with Recorder(path) as rec:
        rec.record(make_scene([rock, up], 1.0), {"volume_up": "ACTIVE"}, [VOLUME_UP])
        rec.record(make_scene([], 1.05), {"volume_up": "IDLE"}, [])
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 2
    first, second = lines
    assert first["t"] == 1.0 and first["states"] == {"volume_up": "ACTIVE"} and first["actions"] == ["TapKeys(vks=(175,))"]
    assert [h["pose"] for h in first["hands"]] == ["open", "rock_on"]      # largest hand first
    assert first["hands"][0]["pointing"] == "up"
    assert first["hands"][0]["fingers"] == {"thumb": True, "index": True, "middle": True, "ring": True, "pinky": True}
    assert set(first["hands"][0]) >= {"fingers", "pose", "pointing", "direction_deg", "direction_len", "width", "palm_center"}
    assert second["hands"] == [] and second["actions"] == []
