"""The one place client values come from: config/client.yaml. The warehouse password and the ports stay in
.env (or the environment Docker Compose sets), because they are secrets and infrastructure, not client values."""

from pathlib import Path

import yaml

ROOT = Path(__file__).parent
REQUIRED = [
    "client.name", "client.currency", "inputs.units", "sites", "areas",
    "rules.unit_types", "rules.price_per_m2_min", "rules.price_per_m2_max", "rules.min_group_size",
    "schedule.cron", "schedule.timezone",
    "report.title", "report.check_area",
    "report.colours.data", "report.colours.text", "report.colours.muted",
    "report.colours.page", "report.colours.line", "report.colours.danger",
    "report.chart_colours.surface", "report.chart_colours.text", "report.chart_colours.muted",
    "report.chart_colours.grid", "report.chart_colours.ours", "report.chart_colours.sites",
    "report.chart_colours.scale",
]


def load_config():
    try:
        cfg = yaml.safe_load((ROOT / "config" / "client.yaml").read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        line = error.problem_mark.line + 1 if getattr(error, "problem_mark", None) else "?"
        raise SystemExit(f"config/client.yaml is not valid YAML near line {line} (quote a value with # or :)")
    for key in REQUIRED:
        node = cfg
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                raise SystemExit(f"config/client.yaml is missing {key}")
            node = node[part]
    for site in cfg["sites"]:
        if not {"id", "pace_seconds"} <= site.keys():
            raise SystemExit(f"config/client.yaml site {site.get('id', '?')}: needs id and pace_seconds")
    for area in cfg["areas"]:
        if not {"id", "name", "sites"} <= area.keys():
            raise SystemExit(f"config/client.yaml area {area.get('id', '?')}: needs id, name and sites")
    if cfg["report"]["check_area"] not in [a["id"] for a in cfg["areas"]]:
        raise SystemExit(f"config/client.yaml report.check_area {cfg['report']['check_area']} is not an id under areas")
    cfg["input_dir"] = ROOT / "data" / "input"
    return cfg
