"""config.py: a wrong config/client.yaml stops with one line naming what is wrong. No network, no warehouse."""

import pytest

import config


def broken(monkeypatch, tmp_path, old, new):
    (tmp_path / "config").mkdir()
    text = (config.ROOT / "config" / "client.yaml").read_text(encoding="utf-8")
    assert old in text
    (tmp_path / "config" / "client.yaml").write_text(text.replace(old, new, 1), encoding="utf-8")
    monkeypatch.setattr(config, "ROOT", tmp_path)


def test_the_demo_config_loads():
    cfg = config.load_config()
    assert [s["id"] for s in cfg["sites"]] == ["realestate", "propertyfinder", "dubizzle", "nawy", "bayut", "aqarmap"]
    assert [a["id"] for a in cfg["areas"]] == ["new-cairo", "new-administrative-capital", "sheikh-zayed",
                                               "sixth-october-city", "north-coast", "mostakbal-city"]


@pytest.mark.parametrize("old, new, message", [
    ("  min_group_size: 10", "  min_group_sizes: 10", "config/client.yaml is missing rules.min_group_size"),
    ("  title: Egypt real estate prices", "  title: Egypt: real estate: prices",
     "config/client.yaml is not valid YAML near line"),
    ("  check_area: new-cairo", "  check_area: alexandria",
     "config/client.yaml report.check_area alexandria is not an id under areas"),
    ("  - {id: nawy, pace_seconds: 2.5}", "  - {id: nawy}", "config/client.yaml site nawy: needs id and pace_seconds"),
])
def test_a_wrong_config_stops_with_one_line(monkeypatch, tmp_path, old, new, message):
    broken(monkeypatch, tmp_path, old, new)
    with pytest.raises(SystemExit) as stop:
        config.load_config()
    assert str(stop.value).startswith(message) and "\n" not in str(stop.value)
