"""Checks of the engine's logic (no rendering):
uv run --with pytest --with numpy --with matplotlib --with python-pptx pytest tests -q"""
import tomllib

import anim


def test_new_pauses_section_has_a_title(tmp_path, monkeypatch):
    monkeypatch.setattr(anim, "PAUSES_FILE", tmp_path / "pauses.toml")
    anim.sync_pauses("intro", 12.0, [(1.9, "flow", 1), (4.5, "flow", 2)])
    section = tomllib.loads((tmp_path / "pauses.toml").read_text())["intro"]
    assert section["title"] == "intro"
    assert section["pauses"] == [1.9, 4.5]
