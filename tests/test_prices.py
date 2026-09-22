"""Reading two providers' published prices, against a saved copy of each page.

This is the module that decides what a customer is charged, so it is the one
with no frappe in it and the one read back hardest. The samples in
`tests/samples/` are the real pages with their scripts, styles and attributes
stripped — the tables and headings are untouched, because those are what the
parsers read.

What the guards are actually for: a provider re-wording its page. That does not
raise, it quietly prices something wrong, and the only thing between us and a
wrong bill is these files failing when the shapes change.
"""

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SAMPLES = Path(__file__).resolve().parent / "samples"


def _prices():
	"""Loaded off the file, because the suite runs without frappe importable."""
	import importlib.util

	at = tree.APP / "one_admin" / "prices.py"
	spec = importlib.util.spec_from_file_location("onedesk_prices", at)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


prices = _prices()


def workers() -> object:
	return prices.workers_ai((SAMPLES / "workers-ai-pricing.html").read_text(encoding="utf-8"))


def gemini() -> object:
	return prices.gemini((SAMPLES / "gemini-pricing.html").read_text(encoding="utf-8"))


def test_the_module_has_no_frappe_in_it():
	"""The AST rather than the text: the docstring says why there is no frappe
	in here, and a guard that grepped would fail on its own reason."""
	import ast

	body = ast.parse((tree.APP / "one_admin" / "prices.py").read_text(encoding="utf-8"))
	for node in ast.walk(body):
		if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef):
			node.body = [
				n
				for n in node.body
				if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))
			]
	assert "frappe" not in ast.unparse(body), "prices.py has to be readable without a site"


# ----------------------------------------------------------------- Workers AI


def test_every_workers_ai_model_on_the_page_is_priced():
	read = workers()
	assert len(read.rates) > 40, "the page stopped yielding model rows"
	assert not read.gaps, [f"{g.model}: {g.wording}" for g in read.gaps][:5]


@pytest.mark.parametrize(
	"model,kind,modality,per,unit",
	[
		("@cf/meta/llama-3.1-8b-instruct-fp8-fast", "input", "text", 1_000_000, "tokens"),
		("@cf/deepseek-ai/deepseek-v4-flash-0731", "cached", "text", 1_000_000, "tokens"),
		("@cf/black-forest-labs/flux-1-schnell", "usage", "image", 1, "512x512 tile"),
		("@cf/black-forest-labs/flux-2-dev", "input", "image", 1, "512x512 tile per step"),
		("@cf/openai/whisper", "usage", "audio", 1, "audio minute"),
		("@cf/deepgram/aura-1", "input", "text", 1_000, "characters"),
		("@cf/microsoft/resnet-50", "usage", "image", 1_000_000, "images"),
	],
)
def test_the_units_are_kept_as_the_provider_wrote_them(model, kind, modality, per, unit):
	"""Seven models, seven different units, nothing converted between them.

	A schema that flattened this to tokens would be wrong for half the
	catalogue, and wrong in a direction nobody notices: silently.
	"""
	rows = workers().rates[model]
	assert any(
		r.kind == kind and r.modality == modality and r.per == per and r.unit == unit for r in rows
	), [(r.kind, r.modality, r.per, r.unit) for r in rows]


def test_a_cache_read_is_not_a_cheaper_input():
	rows = workers().rates["@cf/deepseek-ai/deepseek-v4-flash-0731"]
	cached = next(r for r in rows if r.kind == "cached")
	plain = next(r for r in rows if r.kind == "input")
	assert cached.usd < plain.usd and cached.kind != plain.kind


def test_more_than_one_unit_is_in_use():
	units = {r.unit for rows in workers().rates.values() for r in rows}
	assert len(units) >= 6, f"only {units} — the page has stopped saying units"


# --------------------------------------------------------------------- Gemini


def test_most_gemini_models_are_priced_and_the_rest_say_why():
	read = gemini()
	assert len(read.priced()) > 15
	assert read.gaps, "something is being read that should not be"
	for gap in read.gaps:
		assert gap.wording.strip(), f"{gap.model} has a gap with nothing in it"


def test_a_published_future_price_is_kept_and_not_charged_yet():
	"""Google publishes next year's price beside this year's. Charging the wrong
	side of that date is an error nobody notices for a month."""
	rows = gemini().rates["Gemini 3.8 Flash"]
	inputs = [r for r in rows if r.kind == "input"]
	assert len(inputs) == 2, [(r.usd, r.starts, r.ends) for r in inputs]

	now = prices.in_effect(rows, date(2026, 6, 1))
	later = prices.in_effect(rows, date(2027, 6, 1))
	assert [r.usd for r in now if r.kind == "input"] == [0.75]
	assert [r.usd for r in later if r.kind == "input"] == [1.50]


def test_one_price_covering_three_modalities_becomes_three_rates():
	rows = gemini().rates["Gemini 2.5 Flash-Lite"]
	inputs = {r.modality: r.usd for r in rows if r.kind == "input"}
	assert inputs == {"text": 0.10, "image": 0.10, "video": 0.10, "audio": 0.30}


def test_a_restatement_in_another_unit_is_kept_as_another_rate():
	"""`$0.45 ($0.00012 per image)` is one price said twice, and the second way
	is the one we can meter a picture with."""
	rows = gemini().rates["Gemini Embedding 2"]
	pictures = [r for r in rows if r.modality == "image"]
	assert {(r.per, r.unit) for r in pictures} == {(1_000_000, "tokens"), (1, "image")}


def test_a_storage_charge_sharing_a_cell_is_not_read_as_a_call_price():
	"""Google prices context cache storage per hour in the same cell as the
	cache read. Billed per call it would charge somebody for holding still."""
	rows = gemini().rates["Gemini 3.8 Flash"]
	cached = [r for r in rows if r.kind == "cached"]
	assert {r.usd for r in cached} == {0.075, 0.15}
	assert all("hour" not in r.unit for r in rows)


def test_a_modality_after_the_unit_still_attaches():
	"""`$3.00 or $0.005/min (audio)` is two spellings of one price, and the only
	word saying what it is for sits after the second of them."""
	rows = gemini().rates["Gemini 3.8 Live"]
	by_min = [r for r in rows if r.unit == "min" and r.kind == "input"]
	assert {r.modality for r in by_min} == {"audio", "image", "video"}
	assert any(r.modality == "audio" and r.per == 1_000_000 and r.usd == 3.0 for r in rows)


def test_a_width_is_not_read_as_a_multiplier():
	"""`$0.067 per 1K image` is a picture 1024 wide, not a thousand pictures.

	Read as a multiplier it is a bill a thousand times too large, so the whole
	restatement is left unread and the model goes in front of a person.
	"""
	read = gemini()
	nano = next(name for name in read.rates if name.startswith("Gemini 3.1 Flash Image"))
	assert nano not in read.priced()
	assert any("1K image" in gap.wording for gap in read.gaps if gap.model == nano)
	assert all(r.unit != "image" for r in read.rates[nano])


def test_only_the_tier_we_sell_is_read():
	"""Batch, Flex and Priority are different products with different latencies.
	Offering one would be a decision, and this module makes none."""
	rows = gemini().rates["Gemini 3.8 Flash"]
	assert {r.usd for r in rows if r.kind == "output"} == {3.75, 7.50}


def test_names_from_two_sources_fold_onto_each_other():
	assert prices.fold("Gemini 3.1 Flash Image (Nano Banana 2) 🍌") == "gemini-3-1-flash-image"
	assert prices.fold("gemini-3.1-flash-image") == "gemini-3-1-flash-image"
	assert prices.fold("@cf/meta/llama-3.1-8b") == "cf-meta-llama-3-1-8b"


def test_two_prices_for_the_same_thing_is_a_gap_not_a_coin_toss():
	"""Found by this guard, not by reading: Gemini 2.5 Pro prices a prompt under
	200k tokens at $1.25 and one over at $2.50, and the parser was keeping the
	first and billing every long prompt at half price.

	A context length is a dimension this schema has no field for. Inventing one
	to carry an unused distinction is worse than saying so.
	"""
	read = gemini()
	for name in ("Gemini 2.5 Pro", "Gemini 3.1 Pro Preview"):
		assert name not in read.priced(), f"{name} is being priced from two prices"
		said = [g.wording for g in read.gaps if g.model == name]
		assert any("two prices for the same" in one for one in said), said


def test_a_price_row_this_cannot_read_is_named_rather_than_skipped():
	"""Veo's rows are a model variant each, priced per second of video and
	differing by resolution. Silently skipping them left three video models with
	no price and nothing saying the page had one."""
	read = gemini()
	veo = [g for g in read.gaps if g.model == "Veo 3.1"]
	assert veo, "the Veo table is being passed over without a word"
	assert any("720p" in g.wording for g in veo)
	assert "Veo 3.1" not in read.rates


def test_a_table_with_no_row_this_could_read_says_so():
	read = gemini()
	for name in ("Veo 3.1", "Lyria 3.5"):
		assert any(g.what == "table" for g in read.gaps if g.model == name), name


def test_lyria_is_named_even_though_nothing_could_price_it():
	"""So the matcher can tell a model the page does not mention from one it
	mentions and we could not read — different problems, different answers."""
	said = [g.wording for g in gemini().gaps if g.model == "Lyria 3.5"]
	assert any("per song" in one for one in said), said
