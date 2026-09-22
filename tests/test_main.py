from pathlib import Path

from handcontrol.__main__ import parse_args


def test_defaults():
    a = parse_args([])
    assert (a.preview, a.no_tray, a.camera, a.config, a.verbose) == (False, False, None, None, False)


def test_all_flags():
    a = parse_args(["--preview", "--no-tray", "--camera", "2", "--config", "c.toml", "-v"])
    assert a.preview and a.no_tray and a.verbose
    assert a.camera == 2
    assert a.config == Path("c.toml")
