import json
import re
from functools import cache
from pathlib import Path

APPS = Path(__file__).resolve().parents[2]
SPRITE = APPS / "frappe/frappe/public/icons/lucide/icons.svg"
MARKS = Path(__file__).resolve().parents[1] / "onedesk" / "fixtures" / "custom_icon.json"


@cache
def icons() -> frozenset[str] | None:
	"""Every icon frappe draws: its lucide set and One's own marks
	(fixtures/custom_icon.json). None when frappe is not checked out beside
	this app. The one place a guard asks whether frappe draws an icon."""
	if not SPRITE.exists():
		return None
	drawn = set(re.findall(r'<symbol[^>]*id="(?:icon-)?([\w-]+)"', SPRITE.read_text()))
	for one in json.loads(MARKS.read_text()):
		drawn |= {one["name"], one.get("icon_name") or one["name"]}
	return frozenset(drawn)
