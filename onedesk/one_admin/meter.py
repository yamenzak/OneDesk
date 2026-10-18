"""What a call actually consumed, read out of what the provider answered.

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


def read(provider: str, body: dict, asked: list[Use] | None = None) -> tuple[list[Use], str]:
	"""Everything this response says it consumed, and why if it says nothing.

	`asked` is what we sent — a count of pictures, seconds of audio, diffusion
	steps — and is used only for the parts a provider does not report. It is
	never used to second-guess a number the provider did report.
	"""
	found = _workers_ai(body) if provider == "workers-ai" else _gemini(body)
	if found:
		reported = {use.at for use in found}
		found += [use for use in (asked or []) if use.at not in reported]
		return found, ""
	if asked:
		return list(asked), "the provider reported no usage; metered from what was asked for"
	return [], "the provider reported no usage and nothing was asked for that could be counted"


def _workers_ai(body: dict) -> list[Use]:
	"""`usage`, which carries text tokens and nothing else.

	Wrapped in `result` on the direct API and at the top level on the gateway's
	OpenAI-compatible endpoint. Reading only one of them is a call that answers
	fine and bills its hold because nothing could be metered.
	"""
	said = (body or {}).get("result") or body or {}
	usage = said.get("usage") or {}
	found = []
	for key, kind in (("prompt_tokens", "input"), ("completion_tokens", "output")):
		count = usage.get(key)
		if count:
			found.append(Use(kind=kind, modality="text", unit=TOKENS, count=float(count)))
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
