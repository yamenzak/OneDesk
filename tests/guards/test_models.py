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


def test_the_list_was_read_lately():
	read = date.fromisoformat(LISTED["read_on"])
	assert date.today() - read <= timedelta(days=30), f"models.json was read on {read}: run scripts/models.py"


def test_every_model_used_is_offered_and_not_going():
	for model in sorted(models.used()):
		one = KNOWN.get(model)
		assert one, f"{model} is in one_ai/models.py but neither company lists it"
		assert not one.get("alias"), f"{model} is an alias, which changes underneath a measurement"
		going = one.get("withdrawn_on")
		assert not going or date.fromisoformat(going[:10]) > date.today(), f"{model} was withdrawn on {going}"


def test_a_preview_is_used_only_with_a_reason():
	for model in sorted(models.used()):
		if KNOWN.get(model, {}).get("preview"):
			assert models.PREVIEWS.get(model, "").endswith("."), f"{model} is a preview: say why in PREVIEWS"


def test_every_model_used_has_a_price():
	read = date.fromisoformat(models.CHECKED)
	assert date.today() - read <= timedelta(days=90), f"Google's prices were read on {read}: read them again"
	for model in sorted(models.used()):
		if model.startswith("google/"):
			assert model in models.GOOGLE or model in models.UNPRICED, f"{model} has no price in GOOGLE"
		else:
			assert KNOWN[model].get("price"), f"{model} has no price in Workers AI's listing"


def test_every_kind_has_every_tier_and_never_falls_back_to_itself():
	for kind, tiers in models.USE.items():
		assert set(tiers) == set(models.TIERS), f"{kind} names {sorted(tiers)}, not {models.TIERS}"
		for tier, (first, then) in tiers.items():
			assert first != then, f"{kind} {tier} falls back to itself"
