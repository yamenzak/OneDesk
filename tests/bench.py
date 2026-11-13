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


@cache
def _doctypes() -> dict[str, tuple[Path, ...]]:
	found: dict[str, list[Path]] = {}
	for path in APPS.glob("*/*/*/doctype/*/*.json"):
		if path.stem == path.parent.name:
			found.setdefault(path.stem, []).append(path)
	return {scrub: tuple(paths) for scrub, paths in found.items()}


def doctype_json(scrub: str) -> tuple[Path, ...]:
	"""Each checked-out app's JSON of a record type, by its scrubbed name, in
	the order `APPS.glob("*/*/*/doctype/<scrub>/<scrub>.json")` gives them."""
	return _doctypes().get(scrub, ())
