"""What a call actually consumed, read out of what the model answered.

Pure: the numbers the provider reported, turned into `pricing.Use`. Nothing is
inferred, and a call that answered but could not be metered is not free.
"""

from onedesk.one_admin.pricing import Use

SAID_AS = {
	"TEXT": "text",
	"IMAGE": "image",
	"AUDIO": "audio",
	"VIDEO": "video",
	"DOCUMENT": "other",
}

TOKENS = "tokens"


def read(model: str, body: dict, asked: list[Use] | None = None) -> tuple[list[Use], str]:
	"""Everything this response says it consumed, and why if it says nothing.

	`asked` is what we sent, and is used only for the parts a provider does
	not report; never to second-guess a number it did report.
	"""
	found = _gemini(body) if model.startswith("google/") else _workers_ai(body)
	if found:
		reported = {use.at for use in found}
		found += [use for use in (asked or []) if use.at not in reported]
		return found, ""
	if asked:
		return list(asked), "the provider reported no usage; metered from what was asked for"
	return [], "the provider reported no usage and nothing was asked for that could be counted"


def _workers_ai(body: dict) -> list[Use]:
	"""What Workers AI reported, in whichever shape the model answers in:
	OpenAI's `usage` (talking), `input_tokens` (Clef, Clairic), the cost
	metric under `meta` (vectors), or the length of what was heard (Whisper).
	At the top level or under `result`.
	"""
	said = (body or {}).get("result") or body or {}
	usage = said.get("usage") or {}
	found = []
	cached = float(((usage.get("prompt_tokens_details") or {}).get("cached_tokens")) or 0)
	for key, kind in (("prompt_tokens", "input"), ("input_tokens", "input"), ("completion_tokens", "output"), ("output_tokens", "output")):
		count = float(usage.get(key) or 0)
		if kind == "input" and cached:
			count -= cached
		if count > 0 and not any(use.kind == kind for use in found):
			found.append(Use(kind=kind, modality="text", unit=TOKENS, count=count))
	if cached:
		found.append(Use(kind="cached", modality="text", unit=TOKENS, count=cached))
	meta = said.get("meta") or {}
	if not found and meta.get("cost_metric_name_1") == "input_tokens" and meta.get("cost_metric_value_1"):
		found.append(Use(kind="input", modality="text", unit=TOKENS, count=float(meta["cost_metric_value_1"])))
	heard = (said.get("transcription_info") or {}).get("duration")
	if not found and heard:
		found.append(Use(kind="input", modality="audio", unit="minutes", count=round(float(heard) / 60, 4)))
	return found


def _gemini(body: dict) -> list[Use]:
	"""`usageMetadata`, per modality where it says so and in total where it does not.

	The per-modality breakdown is the part worth having: a prompt of text and a
	picture is two rates on this catalogue, and the total alone could only be
	billed at one of them.
	"""
	usage = (body or {}).get("usageMetadata") or {}
	if not usage:
		return []

	found = []
	cached = float(usage.get("cachedContentTokenCount") or 0)
	for detail, count, kind in (
		("promptTokensDetails", usage.get("promptTokenCount"), "input"),
		("candidatesTokensDetails", usage.get("candidatesTokenCount"), "output"),
	):
		rows = usage.get(detail) or []
		if rows:
			found += _per_modality(rows, kind)
		elif count:
			found.append(Use(kind=kind, modality="text", unit=TOKENS, count=float(count)))

	if cached:
		found = _less(found, "input", cached)
		found.append(Use(kind="cached", modality="text", unit=TOKENS, count=cached))
	return [use for use in found if use.count > 0]


def _per_modality(rows: list, kind: str) -> list[Use]:
	found = []
	for row in rows:
		count = float((row or {}).get("tokenCount") or 0)
		if not count:
			continue
		said = SAID_AS.get(str((row or {}).get("modality") or "").upper(), "other")
		found.append(Use(kind=kind, modality=said, unit=TOKENS, count=count))
	return found


def _less(uses: list[Use], kind: str, count: float) -> list[Use]:
	"""Take `count` off the text line of one kind, without going below nothing."""
	out = []
	for use in uses:
		if use.kind == kind and use.modality == "text" and count > 0:
			taken = min(use.count, count)
			count -= taken
			out.append(
				Use(kind=use.kind, modality=use.modality, unit=use.unit, count=use.count - taken)
			)
			continue
		out.append(use)
	return out
