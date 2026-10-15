"""Every link at the top of a rail carries an icon frappe draws: one without
shows the bare list mark, as OneCRM's Lead and Opportunity did."""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPRITE = Path("/home/frappe/bench1/apps/frappe/frappe/public/icons/lucide/icons.svg")


def test_a_top_row_has_an_icon_frappe_draws():
	drawn = (
		set(re.findall(r'<symbol[^>]*id="(?:icon-)?([\w-]+)"', SPRITE.read_text()))
		if SPRITE.exists()
		else None
	)
	wrong = []
	for path in sorted((ROOT / "onedesk").glob("*/sidebar/*/*.json")):
		for row in json.loads(path.read_text(encoding="utf-8"))["items"]:
			if row.get("child") or row.get("type") != "Link":
				continue
			icon = row.get("icon")
			if not icon:
				wrong.append(f"{path.name}: {row['label']} has no icon")
			elif drawn is not None and icon not in drawn:
				wrong.append(f"{path.name}: {row['label']}'s icon {icon!r} is not in frappe's set")
	if drawn is None:
		pytest.skip("frappe is not checked out beside this app")
	assert not wrong, "\n".join(wrong)
