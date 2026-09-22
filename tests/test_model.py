from pathlib import Path

import pytest

from handcontrol.model import MODEL_URL, ensure_model


def test_downloads_when_missing(tmp_path):
    target = tmp_path / "models" / "hand_landmarker.task"
    calls = []

    def fake_fetch(url, dest):
        calls.append((url, dest))
        Path(dest).write_bytes(b"model-bytes")

    assert ensure_model(target, fetch=fake_fetch) == target
    assert target.read_bytes() == b"model-bytes"
    assert calls == [(MODEL_URL, str(target.with_suffix(".task.part")))]


def test_skips_download_when_present(tmp_path):
    target = tmp_path / "hand_landmarker.task"
    target.write_bytes(b"existing")
    calls = []
    ensure_model(target, fetch=lambda url, dest: calls.append(url))
    assert calls == [] and target.read_bytes() == b"existing"


def test_failure_raises_oserror_and_leaves_no_partial_file(tmp_path):
    target = tmp_path / "hand_landmarker.task"

    def bad_fetch(url, dest):
        Path(dest).write_bytes(b"half")
        raise ConnectionError("network down")

    with pytest.raises(OSError, match="network down"):
        ensure_model(target, fetch=bad_fetch)
    assert not target.exists()
    assert list(tmp_path.iterdir()) == []
