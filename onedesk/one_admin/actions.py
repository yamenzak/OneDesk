"""Turning a job into one call: its kind of work and the workspace's tier,
never a model and never words a workspace adds (docs/AICENTER.md). What
the model is told is `one_ai/jobs.py`'s.
"""


from onedesk.one_admin import gateway
from onedesk.one_admin.faults import Refused
from onedesk.one_ai import jobs, models


def run(
	tenant: str,
	action: str,
	text: str | None = None,
	tier: str | None = None,
	reference: str | None = None,
	turns: list[dict] | None = None,
	tools: list[dict] | None = None,
) -> dict:
	"""One round of one action, run for one workspace and billed to it.

	A round rather than a call, because a model that may look things up answers
	by asking for a tool and has to be called again with what it found. The
	workspace drives that loop: this is stateless, the whole conversation
	arrives every time, and admin still never calls a workspace.
	"""
	job = _job(action)
	tier = tier if tier in models.TIERS else None
	spoken = _conversation(turns, text)
	offered = tools if (tools and job.tools) else None

	answer = gateway.call(
		job.kind,
		tier,
		None,
		tenant,
		caps=_caps(job, tier),
		reference=reference or action,
		system=jobs.told(action) or None,
		turns=spoken,
		tools=offered,
		action=action,
		think=jobs.thinking(job, tier or models.USUAL),
	)
	wants = answer.get("wants") or []
	return {
		"action": action,
		"model": answer.get("model"),
		"done": not wants,
		"turns": spoken + [{"role": "model", "text": answer.get("said") or "", "calls": wants}],
		**answer,
	}


def make(tenant: str, action: str, text: str, tier: str | None = None, reference: str | None = None, voice: str | None = None) -> dict:
	"""A job that makes a voice or a picture rather than words, run for one
	workspace and billed to it. What the model is asked is the job's words
	followed by the workspace's text."""
	job = _job(action)
	tier = tier if tier in models.TIERS else None
	told = jobs.told(action)
	prompt = f"{told}\n\n{text}" if told else text
	return gateway.make(job.kind, tier, prompt, tenant, voice=voice, reference=reference or action, action=action)


# The kinds a model answers in its own shape rather than in words, and what
# each is sent besides the text (docs/AICENTER.md, Reading what arrives).
READERS = {"decide": "questions", "decide_media": "questions", "extract": "fields"}


def read(tenant: str, action: str, state: str, asked: dict, tier: str | None = None, reference: str | None = None, on: str | None = None) -> dict:
	"""One reading job (Clef's questions or Clairic's fields) over one text,
	run for one workspace and billed to it: the answers with their
	probabilities, and which model gave them. `on` is the day relative dates
	are read from."""
	job = _job(action)
	wants = READERS.get(job.kind)
	if not wants:
		raise Refused(f"{action} is not a reading job")
	if not isinstance(asked, dict) or not asked:
		raise Refused(f"{action} asks nothing")
	body = {"state": str(state or "")[: job.takes * 4], wants: asked, **({"reference_date": on} if on and wants == "fields" else {})}
	tier = tier if tier in models.TIERS else None
	answer = gateway.run(job.kind, tier, body, tenant, caps={"input_tokens": job.takes}, reference=reference or action, action=action)
	return {"action": action, "model": answer.get("model"), "credits": answer.get("credits"), "result": answer.get("result")}


def embed(tenant: str, texts: list[str]) -> dict:
	"""Texts as vectors, for one workspace's search by meaning, billed to it.
	Every vector a search compares came from one model, so the caller is told
	which."""
	return gateway.embed(list(texts or []), tenant, reference="embed", action="embed")


def _conversation(turns: list[dict] | None, text: str | None) -> list[dict]:
	"""The conversation so far, checked before it is spoken.

	A workspace sends this and a workspace is not something to be trusted about
	its own limits, so the rounds are counted here rather than there — a loop
	that only the caller could stop is a loop a caller with a bug never stops.
	"""
	if not turns:
		return [gateway.said(text or "")]
	asked = max(
		(at for at, one in enumerate(turns) if one.get("role") == "user" and not one.get("context")),
		default=-1,
	)
	rounds = sum(1 for one in turns[asked + 1 :] if one.get("role") == "model")
	if rounds >= gateway.ROUNDS:
		raise Refused(
			f"this has gone {rounds} rounds, which is as far as it goes; "
			"ask again in smaller pieces"
		)
	return list(turns)


def _job(key: str) -> jobs.Job:
	job = jobs.get(key)
	if not job:
		raise Refused(f"{key} is not a job OneAI does")
	return job


def _caps(job: jobs.Job, tier: str | None) -> dict:
	caps = {"output_tokens": jobs.most(job, tier or models.USUAL)}
	if job.takes:
		caps["input_tokens"] = job.takes
	return caps
