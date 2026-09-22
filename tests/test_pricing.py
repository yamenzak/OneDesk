"""From a provider's rate to a customer's credits, and the metering between.

Two pure modules and a saved response from each provider. Everything here fails
as a wrong number rather than as an exception, which is why it is a table of
cases and not a walk through the code.
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SAMPLES = Path(__file__).resolve().parent / "samples"


def _load(name: str):
	import importlib.util

	at = tree.APP / "one_admin" / f"{name}.py"
	spec = importlib.util.spec_from_file_location(f"onedesk_{name}", at)
	module = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = module
	spec.loader.exec_module(module)
	return module


pricing = _load("pricing")
Use = pricing.Use


def _meter():
	"""Loaded after pricing, because it imports `Use` from it by name."""
	import importlib.util

	at = tree.APP / "one_admin" / "meter.py"
	source = at.read_text(encoding="utf-8").replace(
		"from onedesk.one_admin.pricing import Use", "Use = _USE"
	)
	module = type(sys)("onedesk_meter")
	module._USE = Use
	exec(compile(source, str(at), "exec"), module.__dict__)
	return module


meter = _meter()


@dataclass(frozen=True)
class Rate:
	"""Stands in for `prices.Rate`, which pricing takes structurally."""

	kind: str
	modality: str
	unit: str
	per: int
	usd: float


#: A real model's real rates: Gemini 2.5 Flash-Lite, per million tokens.
FLASH_LITE = [
	Rate("input", "text", "tokens", 1_000_000, 0.10),
	Rate("input", "image", "tokens", 1_000_000, 0.10),
	Rate("output", "text", "tokens", 1_000_000, 0.40),
	Rate("cached", "text", "tokens", 1_000_000, 0.01),
]

#: And one that is not priced in tokens at all.
FLUX = [
	Rate("usage", "image", "512x512 tile", 1, 0.0000528),
	Rate("usage", "image", "step", 1, 0.0001056),
]


def test_both_modules_have_no_frappe_in_them():
	import ast

	for name in ("pricing", "meter"):
		body = ast.parse((tree.APP / "one_admin" / f"{name}.py").read_text(encoding="utf-8"))
		for node in ast.walk(body):
			if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef):
				node.body = [
					n
					for n in node.body
					if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))
				]
		assert "frappe" not in ast.unparse(body), name


# ------------------------------------------------------------------- pricing


def test_a_rate_and_a_use_meet_on_all_three_or_not_at_all():
	"""Nothing converts between units, so nothing falls back to a near match."""
	usd, unpriced = pricing.cost(FLASH_LITE, [Use("input", "audio", "tokens", 1_000_000)])
	assert usd == 0 and [u.modality for u in unpriced] == ["audio"]


def test_what_a_real_call_costs():
	usd, unpriced = pricing.cost(
		FLASH_LITE,
		[Use("input", "text", "tokens", 32), Use("output", "text", "tokens", 12)],
	)
	assert not unpriced
	assert usd == round(32 / 1_000_000 * 0.10 + 12 / 1_000_000 * 0.40, pricing.CENTS)


def test_a_fraction_of_a_cent_is_not_rounded_away():
	"""A tile is $0.0000528. Rounded to cents before the markup it is free."""
	usd, _ = pricing.cost(FLUX, [Use("usage", "image", "512x512 tile", 1)])
	assert usd == 0.0000528


def test_the_markup_and_the_rate_turn_dollars_into_credits():
	made = pricing.bill(FLASH_LITE, [Use("output", "text", "tokens", 1_000_000)], 2.0, 1000)
	assert made.usd == 0.40
	assert made.credits == 800.0
	assert made.whole


def test_a_use_with_no_rate_makes_the_whole_bill_not_a_bill():
	made = pricing.bill(
		FLASH_LITE,
		[Use("output", "text", "tokens", 1_000), Use("usage", "audio", "audio minute", 3)],
		2.0,
		1000,
	)
	assert not made.whole
	assert [u.unit for u in made.unpriced] == ["audio minute"]


@pytest.mark.parametrize("markup,per_dollar", [(0, 1000), (2.0, 0), (-1, 1000)])
def test_neither_number_has_a_default(markup, per_dollar):
	"""A provider publishes what a call costs it, never what it should cost
	anybody else. A default here would be inventing somebody's margin."""
	with pytest.raises(pricing.Unpriceable):
		pricing.bill(FLASH_LITE, [Use("output", "text", "tokens", 10)], markup, per_dollar)


def test_a_ceiling_is_priced_from_the_caps_a_caller_declared():
	most = pricing.ceiling(FLASH_LITE, {"output_tokens": 512, "input_tokens": 4000}, 2.0, 1000)
	assert most.credits == round((512 / 1e6 * 0.40 + 4000 / 1e6 * 0.10) * 2.0 * 1000, 6)
	assert all(use.asked for use, _ in most.lines)


def test_a_cap_that_does_not_apply_is_not_a_refusal():
	"""An action capping output tokens against a model priced per picture has
	capped something that does not apply. The settle is where that is caught."""
	most = pricing.ceiling(FLUX, {"output_tokens": 512}, 2.0, 1000)
	assert most.credits == 0


# -------------------------------------------------------------------- meter


def _sample(name: str) -> dict:
	return json.loads((SAMPLES / name).read_text(encoding="utf-8"))


def test_workers_ai_reports_text_tokens_and_nothing_else():
	used, why = meter.read("workers-ai", _sample("workers-ai-answer.json"))
	assert not why
	assert {(u.kind, u.count) for u in used} == {("input", 18.0), ("output", 7.0)}
	assert all(not u.asked for u in used)


def test_a_response_with_no_usage_falls_back_to_what_was_asked_for():
	"""Workers AI reports nothing for pictures and speech, so those are metered
	from the parameters we sent — which we know, because we sent them."""
	asked = [Use("usage", "image", "step", 4, asked=True)]
	used, why = meter.read("workers-ai", _sample("workers-ai-answer-no-usage.json"), asked)
	assert used == asked and "no usage" in why


def test_a_response_with_no_usage_and_nothing_asked_for_says_so():
	used, why = meter.read("workers-ai", _sample("workers-ai-answer-no-usage.json"))
	assert used == [] and why


def test_gemini_is_metered_per_modality():
	"""A prompt of text and a picture is two rates on this catalogue, and the
	total alone could only ever be billed at one of them."""
	used, why = meter.read("google-ai-studio", _sample("gemini-answer.json"))
	assert not why
	assert {(u.kind, u.modality, u.count) for u in used} == {
		("input", "text", 32.0),
		("input", "image", 1258.0),
		("output", "text", 12.0),
	}


def test_a_cached_prompt_is_not_charged_twice():
	"""Google counts cached tokens inside the prompt total as well. Left alone,
	the same four thousand tokens are billed at the input rate and again at the
	cache rate."""
	used, _ = meter.read("google-ai-studio", _sample("gemini-answer-cached.json"))
	by_kind = {(u.kind, u.modality): u.count for u in used}
	assert by_kind[("input", "text")] == 1000.0
	assert by_kind[("cached", "text")] == 4000.0
	assert by_kind[("output", "text")] == 40.0


def test_a_reported_line_beats_one_we_asked_for():
	"""What we sent is only ever used for what a provider does not report."""
	asked = [Use("input", "text", "tokens", 999, asked=True)]
	used, _ = meter.read("workers-ai", _sample("workers-ai-answer.json"), asked)
	assert {(u.kind, u.count) for u in used if u.kind == "input"} == {("input", 18.0)}


def test_a_metered_gemini_call_prices_end_to_end():
	used, _ = meter.read("google-ai-studio", _sample("gemini-answer.json"))
	made = pricing.bill(FLASH_LITE, used, 2.0, 1000)
	assert made.whole
	expected = (32 * 0.10 + 1258 * 0.10 + 12 * 0.40) / 1_000_000
	assert made.credits == round(expected * 2.0 * 1000, 6)
