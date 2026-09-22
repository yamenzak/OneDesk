"""What a call actually consumed, read out of what the provider answered.

Pure, and the shortest module in this arc, because the whole of it is: take the
numbers the provider reported and turn them into `pricing.Use`. Nothing is
inferred, nothing is estimated, and a response with no usage in it comes back
saying so rather than coming back as nothing.

**The two providers report differently, and that is the reason the rate schema
is unit-aware.** Gemini's `usageMetadata` carries token counts per modality for
the prompt, the cache and the output, so a multimodal call is exactly meterable.
Workers AI reports tokens for text and nothing at all for pictures or speech, so
those are metered from what we asked for — which we know, because we sent it.

**A call that answered but could not be metered is not free.** `read` returns
what it found and the caller charges the hold, which is the only honest answer:
the provider billed us for it either way.
"""

from onedesk.one_admin.pricing import Use

#: Gemini's own word for a modality, which is upper case and one of a handful.
SAID_AS = {
	"TEXT": "text",
	"IMAGE": "image",
	"AUDIO": "audio",
	"VIDEO": "video",
	"DOCUMENT": "other",
}

#: Everything either provider counts in, once counted. Both bill text per
#: million tokens and both report a count of tokens, so the unit is the same
#: word — which is a coincidence rather than a rule, and is why it is written
#: down here rather than assumed at the call site.
TOKENS = "tokens"


def read(provider: str, body: dict, asked: list[Use] | None = None) -> tuple[list[Use], str]:
	"""Everything this response says it consumed, and why if it says nothing.

	`asked` is what we sent — a count of pictures, seconds of audio, diffusion
	steps — and is used only for the parts a provider does not report. It is
	never used to second-guess a number the provider did report.
	"""
	found = _workers_ai(body) if provider == "workers-ai" else _gemini(body)
	if found:
		# Anything we asked for that the provider did not report on: a picture's
		# tiles, an audio minute. Reported lines win where the two overlap.
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
		# Cached tokens are counted inside the prompt total as well, so the
		# input line comes down by what the cache covered — otherwise the same
		# tokens are charged twice, once at each rate.
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
