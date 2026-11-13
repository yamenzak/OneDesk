"""The models OneAI uses are ones Cloudflare and Google still offer, priced,
and chosen on purpose (docs/AICENTER.md, Models). Reads the list
scripts/models.py wrote, without a network."""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from onedesk.one_ai import models  # noqa: E402

LISTED = json.loads((ROOT / "onedesk" / "one_ai" / "models.json").read_text(encoding="utf-8"))
KNOWN = {one["id"]: one for one in LISTED["models"]}


def stale(read_on: str, days: int, today: date) -> bool:
	"""Whether a list read on `read_on` is older than `days`. Pure."""
	return today - date.fromisoformat(read_on) > timedelta(days=days)


def unoffered(used, known: dict, today: date) -> list[str]:
	"""The models used that neither company lists, that are aliases, or that are withdrawn. Pure."""
	out = []
	for model in sorted(used):
		one = known.get(model)
		if not one:
			out.append(f"{model} is in one_ai/models.py but neither company lists it")
			continue
		if one.get("alias"):
			out.append(f"{model} is an alias, which changes underneath a measurement")
		going = one.get("withdrawn_on")
		if going and date.fromisoformat(going[:10]) <= today:
			out.append(f"{model} was withdrawn on {going}")
	return out


def unexplained_previews(used, known: dict, previews: dict) -> list[str]:
	"""The previews used without a reason in PREVIEWS. Pure."""
	return [
		f"{model} is a preview: say why in PREVIEWS"
		for model in sorted(used)
		if known.get(model, {}).get("preview") and not previews.get(model, "").endswith(".")
	]


def unpriced(used, known: dict, google: dict, unpriced_ok) -> list[str]:
	"""The models used with no price. Pure."""
	out = []
	for model in sorted(used):
		if model.startswith("google/"):
			if model not in google and model not in unpriced_ok:
				out.append(f"{model} has no price in GOOGLE")
		elif not known[model].get("price"):
			out.append(f"{model} has no price in Workers AI's listing")
	return out


def bad_tiers(use: dict, wanted) -> list[str]:
	"""A kind missing a tier, or a tier falling back to itself. Pure."""
	out = []
	for kind, tiers in use.items():
		if set(tiers) != set(wanted):
			out.append(f"{kind} names {sorted(tiers)}, not {wanted}")
		out += [f"{kind} {tier} falls back to itself" for tier, (first, then) in tiers.items() if first == then]
	return out


def test_the_list_was_read_lately():
	assert not stale(LISTED["read_on"], 30, date.today()), f"models.json was read on {LISTED['read_on']}: run scripts/models.py"


def test_every_model_used_is_offered_and_not_going():
	found = unoffered(models.used(), KNOWN, date.today())
	assert not found, "\n".join(found)


def test_a_preview_is_used_only_with_a_reason():
	found = unexplained_previews(models.used(), KNOWN, models.PREVIEWS)
	assert not found, "\n".join(found)


def test_every_model_used_has_a_price():
	assert not stale(models.CHECKED, 90, date.today()), f"Google's prices were read on {models.CHECKED}: read them again"
	found = unpriced(models.used(), KNOWN, models.GOOGLE, models.UNPRICED)
	assert not found, "\n".join(found)


def test_every_kind_has_every_tier_and_never_falls_back_to_itself():
	found = bad_tiers(models.USE, models.TIERS)
	assert not found, "\n".join(found)


def test_the_model_rules_catch_their_examples():
	today = date(2026, 11, 13)
	assert stale("2026-09-01", 30, today) and not stale("2026-11-01", 30, today)
	known = {
		"a/alias": {"alias": True, "price": [1]},
		"a/gone": {"withdrawn_on": "2026-10-01T00:00", "price": [1]},
		"a/fine": {"withdrawn_on": "2027-01-01", "price": [1]},
		"a/preview": {"preview": True},
	}
	assert len(unoffered({"a/missing", "a/alias", "a/gone", "a/fine"}, known, today)) == 3
	assert not unoffered({"a/fine"}, known, today)
	assert unexplained_previews({"a/preview"}, known, {})
	assert not unexplained_previews({"a/preview"}, known, {"a/preview": "Only it reads images."})
	assert unpriced({"google/x", "a/preview", "a/fine"}, known, {}, set()) == [
		"a/preview has no price in Workers AI's listing",
		"google/x has no price in GOOGLE",
	]
	assert len(bad_tiers({"chat": {"fast": ("a", "a")}, "read": {"fast": ("a", "b"), "deep": ("c", None)}}, ("fast", "deep"))) == 2
