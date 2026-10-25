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
	spoken = _conversation(turns, text)
	offered = tools if (tools and job.tools) else None

	answer = gateway.call(
		job.kind,
		tier if tier in models.TIERS else None,
		None,
		tenant,
		caps=_caps(job),
		reference=reference or action,
		system=jobs.told(action),
		turns=spoken,
		tools=offered,
		action=action,
	)
	wants = answer.get("wants") or []
	return {
		"action": action,
		"model": answer.get("model"),
		"done": not wants,
		"turns": spoken + [{"role": "model", "text": answer.get("said") or "", "calls": wants}],
		**answer,
	}


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


def _caps(job: jobs.Job) -> dict:
	caps = {"output_tokens": job.most}
	if job.takes:
		caps["input_tokens"] = job.takes
	return caps
