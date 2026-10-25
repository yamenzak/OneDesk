"""Which model does what, by tier, and what Google charges (docs/AICENTER.md,
Models). Ids are as Cloudflare's REST endpoint takes them, `@cf/...` and
`google/...`; `scripts/models.py` lists both companies' models into
`models.json`, and `tests/guards/test_models.py` holds this file to it.
Pure, so the guard needs no site."""

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

LISTED = Path(__file__).with_name("models.json")

TIERS = ("fast", "balanced", "full")

# Each kind of work, per tier: the model first asked, then the one that
# answers when it can't, on the other company where there is one.
USE = {
	"talk": {
		"fast": ("@cf/google/gemma-4-26b-a4b-it", "google/gemini-3.1-flash-lite"),
		"balanced": ("@cf/zai-org/glm-5.3-flash", "google/gemini-3.5-flash-lite"),
		"full": ("google/gemini-3.8-flash", "@cf/moonshotai/kimi-k2.6"),
	},
	"build": {
		"fast": ("google/gemini-3.5-flash-lite", "@cf/google/gemma-4-26b-a4b-it"),
		"balanced": ("google/gemini-3.8-flash", "@cf/zai-org/glm-5.3"),
		"full": ("google/gemini-3.1-pro-preview", "google/gemini-2.5-pro"),
	},
	"decide": {
		"fast": ("@cf/cloudflare/clef-flash", "@cf/cloudflare/clef"),
		"balanced": ("@cf/cloudflare/clef", "@cf/cloudflare/clef-flash"),
		"full": ("@cf/cloudflare/clef", "@cf/cloudflare/clef-flash"),
	},
	"extract": {tier: ("@cf/cloudflare/clairic", "@cf/zai-org/glm-5.3-flash") for tier in TIERS},
	"see": {tier: ("@cf/google/gemma-4-26b-a4b-it", "google/gemini-3.5-flash-lite") for tier in TIERS},
	"hear": {
		"fast": ("@cf/openai/whisper-large-v3-turbo", "google/gemini-3.5-transcribe"),
		"balanced": ("@cf/openai/whisper-large-v3-turbo", "google/gemini-3.5-transcribe"),
		"full": ("google/gemini-3.5-transcribe", "@cf/openai/whisper-large-v3-turbo"),
	},
	# Text to speech. Only Gemini's voices speak Arabic; Workers AI's MeloTTS
	# stands behind them for the languages it has.
	"speak": {
		"fast": ("google/gemini-3.8-flash-lite-tts", "@cf/myshell-ai/melotts"),
		"balanced": ("google/gemini-3.8-flash-tts", "google/gemini-3.8-flash-lite-tts"),
		"full": ("google/gemini-3.8-flash-tts", "google/gemini-3.8-flash-lite-tts"),
	},
	"embed": {tier: ("@cf/baai/bge-m3", "@cf/qwen/qwen3-embedding-0.6b") for tier in TIERS},
	"guard": {tier: ("@cf/meta/llama-guard-3-8b", None) for tier in TIERS},
	# For the module that makes pictures, music and video; nothing uses them yet.
	"picture": {
		"fast": ("google/gemini-3.1-flash-lite-image", "google/gemini-3.1-flash-image"),
		"balanced": ("google/gemini-3.1-flash-image", "google/gemini-3.1-flash-lite-image"),
		"full": ("google/gemini-3-pro-image", "google/gemini-3.1-flash-image"),
	},
	"music": {
		"fast": ("google/lyria-3-clip-preview", "google/lyria-3.5"),
		"balanced": ("google/lyria-3.5", "google/lyria-3-pro-preview"),
		"full": ("google/lyria-3.5", "google/lyria-3-pro-preview"),
	},
	"video": {
		"fast": ("google/veo-3.1-fast-generate-preview", "google/gemini-omni-1.1-flash"),
		"balanced": ("google/veo-3.1-fast-generate-preview", "google/veo-3.1-generate-preview"),
		"full": ("google/veo-3.1-generate-preview", "google/veo-3.1-fast-generate-preview"),
	},
}

# A preview may be withdrawn without notice, so one is used only where there
# is nothing stable that does the job, and says why.
PREVIEWS = {
	"google/gemini-3.1-pro-preview": "Google's own Pro alias points to it; 2.5 Pro is the stable fallback.",
	"google/lyria-3-clip-preview": "The only thirty-second music model.",
	"google/lyria-3-pro-preview": "Behind Lyria 3.5 only, for a full song when 3.5 can't answer.",
	"google/veo-3.1-generate-preview": "Every Veo model is a preview.",
	"google/veo-3.1-fast-generate-preview": "Every Veo model is a preview.",
	"@cf/cloudflare/clairic": "Cloudflare's reading models are previews; the talk model stands behind them.",
	"@cf/cloudflare/clef": "Cloudflare's reading models are previews; the talk model stands behind them.",
	"@cf/cloudflare/clef-flash": "Cloudflare's reading models are previews; the talk model stands behind them.",
}

# Google's paid prices in dollars, from ai.google.dev/gemini-api/docs/pricing,
# read on CHECKED. Per million tokens unless `per` says otherwise; `from` is
# the day a price starts, when Google has announced a change.
CHECKED = "2026-10-25"
GOOGLE = {
	"google/gemini-3.8-flash": [
		{"in": 0.75, "out": 3.75},
		{"from": "2027-01-01", "in": 1.50, "out": 7.50},
	],
	"google/gemini-3.6-flash": [
		{"in": 0.75, "out": 3.75},
		{"from": "2027-01-01", "in": 1.50, "out": 7.50},
	],
	"google/gemini-3.5-flash-lite": [{"in": 0.30, "out": 2.50}],
	"google/gemini-3.1-flash-lite": [{"in": 0.25, "out": 1.50}],
	"google/gemini-3.1-pro-preview": [{"in": 2.00, "out": 12.00, "above": 200_000, "in_above": 4.00, "out_above": 18.00}],
	"google/gemini-4-argon": [
		{"in": 2.00, "out": 10.00},
		{"from": "2026-12-01", "in": 4.00, "out": 20.00},
	],
	"google/gemini-2.5-flash": [{"in": 0.30, "out": 2.50}],
	"google/gemini-2.5-pro": [{"in": 1.25, "out": 10.00, "above": 200_000, "in_above": 2.50, "out_above": 15.00}],
	"google/gemini-2.5-flash-lite": [{"in": 0.10, "out": 0.40}],
	"google/gemini-3.5-transcribe": [{"per": "minute", "in": 0.003, "out": 0.002}],
	"google/gemini-3.8-flash-tts": [
		{"in": 0.50, "out": 9.00},
		{"from": "2027-01-01", "in": 1.00, "out": 18.00},
	],
	"google/gemini-3.8-flash-lite-tts": [
		{"in": 0.50, "out": 6.00},
		{"from": "2027-01-01", "in": 1.00, "out": 12.00},
	],
	"google/gemini-3.1-flash-lite-image": [{"per": "image", "out": 0.0336}],
	"google/gemini-3.1-flash-image": [{"per": "image", "out": 0.067}],
	"google/gemini-3-pro-image": [{"per": "image", "out": 0.134}],
	"google/gemini-omni-1.1-flash": [{"per": "second", "out": 0.10}],
	"google/lyria-3.5": [{"per": "song", "out": 0.08}],
	"google/lyria-3-pro-preview": [{"per": "song", "out": 0.08}],
	"google/lyria-3-clip-preview": [{"per": "song", "out": 0.04}],
	"google/gemini-embedding-2": [{"in": 0.20}],
}

# Not on Google's pricing page when it was read; until it is, a call is
# charged its hold.
UNPRICED = {
	"google/veo-3.1-generate-preview",
	"google/veo-3.1-fast-generate-preview",
}


def used() -> set[str]:
	"""Every model this file names."""
	return {one for kind in USE.values() for pair in kind.values() for one in pair if one}


USUAL = "balanced"


def pick(kind: str, tier: str | None = None, types: tuple = ()) -> list[str]:
	"""The models to ask for this kind of work at this tier, in order, leaving
	out any that cannot read every file type sent."""
	first, then = USE[kind][tier if tier in TIERS else USUAL]
	return [one for one in (first, then) if one and all(reads(one, kind_of) for kind_of in types)]


def reads(model: str, mime: str) -> bool:
	"""Whether a model takes a file of this type: Gemini takes documents,
	pictures, sound and video; Whisper sound; a Workers AI model with vision,
	pictures."""
	if model.startswith("google/"):
		return mime == "application/pdf" or mime.split("/")[0] in ("image", "audio", "video", "text")
	one = listed().get(model) or {}
	if one.get("kind") == "hear":
		return mime.startswith("audio/")
	return bool(one.get("vision")) and mime.startswith("image/")


_LISTED: dict = {}


def listed() -> dict:
	"""models.json by id, read once."""
	if not _LISTED:
		_LISTED.update({one["id"]: one for one in json.loads(LISTED.read_text(encoding="utf-8"))["models"]})
	return _LISTED


@dataclass(frozen=True)
class Rate:
	"""One price, in the shape `one_admin/pricing.py` bills with."""

	kind: str
	modality: str
	unit: str
	per: float
	usd: float


MILLION = 1_000_000

# Workers AI's units, as rates.
UNITS = {
	"per M input tokens": ("input", "text", "tokens", MILLION),
	"per M output tokens": ("output", "text", "tokens", MILLION),
	"per M cached input tokens": ("cached", "text", "tokens", MILLION),
	"per audio minute": ("input", "audio", "minutes", 1),
	"per 1k characters": ("input", "text", "characters", 1000),
}

# What one Google price is per.
PER = {"minute": ("audio", "minutes"), "image": ("image", "images"), "song": ("audio", "songs"), "second": ("video", "seconds")}


def rates(model: str, on: str | None = None) -> list[Rate]:
	"""What a model costs on a day, from Workers AI's listing or GOOGLE."""
	if model.startswith("google/"):
		day = on or date.today().isoformat()
		current = [one for one in GOOGLE.get(model, []) if (one.get("from") or "") <= day]
		if not current:
			return []
		price = current[-1]
		if price.get("per"):
			modality, unit = PER[price["per"]]
			found = [Rate("input", modality, unit, 1, price["in"])] if price.get("in") else []
			return found + ([Rate("output", modality, unit, 1, price["out"])] if price.get("out") else [])
		found = [Rate("input", modality, "tokens", MILLION, price["in"]) for modality in ("text", "image", "video", "audio", "other")]
		found.append(Rate("cached", "text", "tokens", MILLION, round(price["in"] / 10, 6)))
		if price.get("out"):
			found.append(Rate("output", "text", "tokens", MILLION, price["out"]))
		return found
	found = []
	for one in (listed().get(model) or {}).get("price") or []:
		unit = UNITS.get(one["unit"])
		if unit:
			found.append(Rate(*unit, one["usd"]))
	return found
