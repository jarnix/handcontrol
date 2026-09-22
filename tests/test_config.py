from handcontrol.config import Settings, load_settings, settings_from_dict


def test_defaults_match_spec():
    s = Settings()
    assert (s.camera.index, s.camera.width, s.camera.height) == (0, 1280, 720)
    assert s.tracker.min_hand_detection_confidence == 0.5
    assert s.hand.finger_extended_angle_deg == 150.0
    assert s.hand.fingers_joined_max_m == 0.03
    assert s.hand.vertical_max_deg == 35.0
    assert s.hand.min_direction_len == 0.6
    assert (s.start_menu.fist_frames, s.start_menu.open_within_frames, s.start_menu.cooldown_s) == (6, 12, 1.5)
    assert (s.youtube.hold_frames, s.youtube.cooldown_s, s.youtube.url) == (18, 2.0, "https://www.youtube.com")
    assert (s.show_desktop.hold_frames, s.show_desktop.cooldown_s) == (18, 1.5)
    assert (s.volume.engage_frames, s.volume.repeat_frames) == (10, 5)
    assert s.scroll.engage_frames == 3
    assert s.scroll.release_frames == 5
    assert s.scroll.deadzone_widths == 0.02
    assert s.scroll.gain_notches_per_width == 3.0
    assert s.scroll.smoothing == 0.5
    assert s.scroll.wheel_step == 120


def test_partial_override_keeps_other_defaults():
    s = settings_from_dict({"scroll": {"gain_notches_per_width": 8.0}, "youtube": {"url": "https://example.com"}})
    assert s.scroll.gain_notches_per_width == 8.0
    assert s.scroll.wheel_step == 120
    assert s.youtube.url == "https://example.com"
    assert s.youtube.hold_frames == 18


def test_unknown_keys_and_sections_are_ignored():
    s = settings_from_dict({"scroll": {"bogus": 1}, "nonsense": {"a": 1}})
    assert s == Settings()


def test_non_table_section_is_ignored():
    assert settings_from_dict({"scroll": 5}) == Settings()


def test_missing_file_gives_defaults(tmp_path):
    assert load_settings(tmp_path / "nope.toml") == Settings()


def test_file_override(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text("[start_menu]\ncooldown_s = 3.0\n[volume]\nrepeat_frames = 2\n", encoding="utf-8")
    s = load_settings(p)
    assert s.start_menu.cooldown_s == 3.0
    assert s.volume.repeat_frames == 2


def test_malformed_file_falls_back_to_defaults(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text("[start_menu\nthis is not toml", encoding="utf-8")
    assert load_settings(p) == Settings()
