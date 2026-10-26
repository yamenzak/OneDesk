"""Every model call, through our Cloudflare gateway, holding no provider key
(docs/AICENTER.md, Cloudflare). Workers AI is reached on Cloudflare's REST
endpoints with the gateway named; Gemini on the gateway's Google route, in
Google's own shape, where it reads documents and sound. Which model answers
is `one_ai/models.py`'s, by kind of work and tier; `call`, `run` and `embed`
hold, call, and settle what it cost.
"""

import json
import re
from datetime import date

import frappe
import requests

from onedesk.one_admin import faults, ledger, meter, pricing, site
from onedesk.one_admin.faults import Again, Refused
from onedesk.one_ai import models

API = "https://api.cloudflare.com/client/v4/accounts/{account}/ai"
URL = "https://gateway.ai.cloudflare.com/v1"

TIMEOUT = 60

THOUGHT = 110

HEADER = "cf-aig-authorization"

GATEWAY = "cf-aig-gateway-id"

TAG = "cf-aig-metadata"

FRESH = "cf-aig-skip-cache"

# Cloudflare keeps the counts and the cost of a call, never what was in it.
UNSEEN = {"cf-aig-collect-log-payload": "false"}


MOST_TEXTS = 64

ROUNDS = 8

MOST = 512


def said(text: str, role: str = "user", files: list[dict] | None = None) -> dict:
	"""One turn, in our shape. The only place a turn is built by hand."""
	return {"role": role, "text": text or "", "calls": [], "files": files or []}


def _headers(settings: dict, google: bool, tenant: str | None, tags: dict, fresh: bool = False) -> dict:
	"""Who we are to the gateway, what to keep, and the workspace's tags."""
	headers = {"Content-Type": "application/json", **UNSEEN}
	if google:
		headers[HEADER] = f"Bearer {settings['token']}"
	else:
		headers["Authorization"] = f"Bearer {settings['token']}"
		headers[GATEWAY] = settings["gateway"]
	said_tags = {key: value for key, value in {"tenant": tenant, **tags}.items() if value}
	if said_tags:
		headers[TAG] = json.dumps(said_tags)
	if fresh:
		headers[FRESH] = "true"
	return headers


def _post(model: str, where: str, headers: dict, body: dict, timeout: int = TIMEOUT):
	try:
		answer = requests.post(where, headers=headers, data=json.dumps(body), timeout=timeout)
	except requests.Timeout as raised:
		raise Again(f"{model} timed out") from raised
	except requests.RequestException as raised:
		raise Again(f"{model} could not be reached: {raised}") from raised
	return answer


def talk(
	model: str,
	turns: list[dict],
	most: int = MOST,
	tenant: str | None = None,
	system: str | None = None,
	tools: list[dict] | None = None,
	fresh: bool = False,
	tags: dict | None = None,
	think: bool = False,
) -> tuple[str, list[dict], dict]:
	"""One model, one round: the words, what it asked for, and the whole body,
	which carries the usage. Not billed; `call` is."""
	site.require_admin()
	settings = _settings()
	google = model.startswith("google/")
	headers = _headers(settings, google, tenant, tags or {}, fresh)
	timeout = THOUGHT if think else TIMEOUT
	if google:
		name = model.removeprefix("google/")
		where = f"{settings['url'].rstrip('/')}/{settings['account']}/{settings['gateway']}/google-ai-studio/v1beta/models/{name}:generateContent"
		body = {
			"contents": [_gemini_turn(one) for one in turns],
			"generationConfig": {"maxOutputTokens": most, **({} if think else models.quiet(model))},
			**({"systemInstruction": {"parts": [{"text": system}]}} if system else {}),
			**({"tools": [{"functionDeclarations": tools}]} if tools else {}),
		}
		answer = _post(model, where, headers, body, timeout)
		return _answered(model, answer, _first_part, _gemini_calls)
	body = {
		"model": model,
		"messages": ([{"role": "system", "content": system}] if system else []) + [_openai_turn(one) for one in turns],
		"max_tokens": most,
		**({} if think else models.quiet(model)),
		**({"tools": [{"type": "function", "function": one} for one in tools]} if tools else {}),
	}
	answer = _post(model, f"{API.format(**settings)}/v1/chat/completions", headers, body, timeout)
	return _answered(model, answer, _workers_ai_said, _openai_calls)


def _run(model: str, body: dict, tenant: str | None, tags: dict | None = None) -> dict:
	"""One Workers AI model in its own shape (`/ai/run`): reading, hearing,
	vectors. The whole body."""
	site.require_admin()
	settings = _settings()
	answer = _post(model, f"{API.format(**settings)}/run/{model}", _headers(settings, False, tenant, tags or {}), body)
	if answer.status_code != 200:
		raise faults.raised(model, answer.status_code, _detail(answer))
	try:
		return answer.json()
	except ValueError as raised:
		raise Refused(f"{model} answered 200 with something that is not JSON", answer.status_code, answer.text[: faults.KEPT]) from raised


def call(
	kind: str,
	tier: str | None,
	prompt: str | None,
	tenant: str,
	caps: dict | None = None,
	reference: str | None = None,
	system: str | None = None,
	turns: list[dict] | None = None,
	tools: list[dict] | None = None,
	action: str | None = None,
	think: bool = False,
) -> dict:
	"""One round of a kind of work, billed: hold a ceiling, ask the first
	model and then its fallback, settle what the one that answered cost.
	A model thinks only when `think` says so (one_ai/jobs.py)."""
	site.require_admin()
	spoken = turns or [said(prompt or "")]
	types = tuple(sorted({one.get("type") or "" for turn in spoken for one in (turn.get("files") or []) if one.get("data")}))
	asked = models.pick(kind, tier, types)
	if not asked:
		raise Refused(frappe._("No model here reads {0}.").format(", ".join(types)))
	money = _money()
	tags = {"job": action or kind, "tier": tier or models.USUAL}
	most = _ceiling(asked, caps or {}, money)
	holding = ledger.reserve(tenant, max(most, _LEAST), why=asked[0], reference=reference, action=action)
	try:
		answered, (words, wants, body) = _first_that_answers(
			asked, lambda model: _said(model, spoken, caps or {}, tenant, system, tools, tags, think)
		)
	except Exception:
		ledger.release(holding)
		raise
	return _settled(holding, answered, body, caps or {}, money, most, {"said": words, "wants": wants, "model": answered})


def run(kind: str, tier: str | None, body: dict, tenant: str, caps: dict | None = None, reference: str | None = None, action: str | None = None) -> dict:
	"""One round of a Workers AI model in its own shape (Clef, Clairic,
	Whisper), billed like `call`."""
	site.require_admin()
	asked = [one for one in models.pick(kind, tier) if one.startswith("@cf/")]
	if not asked:
		raise Refused(f"no Workers AI model does {kind}")
	money = _money()
	most = _ceiling(asked, caps or {}, money)
	holding = ledger.reserve(tenant, max(most, _LEAST), why=asked[0], reference=reference, action=action)
	tags = {"job": action or kind, "tier": tier or models.USUAL}
	try:
		answered, said_body = _first_that_answers(asked, lambda model: _run(model, body, tenant, tags))
	except Exception:
		ledger.release(holding)
		raise
	return _settled(holding, answered, said_body, caps or {}, money, most, {"result": said_body.get("result"), "model": answered})


def embed(texts: list[str], tenant: str, reference: str | None = None, action: str | None = None) -> dict:
	"""Texts as vectors, billed: hold as if every character were a token,
	settle what the model reported. Every vector one search compares came
	from one model, so the caller is told which."""
	site.require_admin()
	texts = [str(one or " ") for one in texts][:MOST_TEXTS]
	asked = models.pick("embed")[:1]
	money = _money()
	caps = {"input_tokens": sum(len(one) for one in texts)}
	most = _ceiling(asked, caps, money)
	holding = ledger.reserve(tenant, max(most, _LEAST), why=asked[0], reference=reference, action=action)
	try:
		body = _run(asked[0], {"text": texts}, tenant, {"job": action or "embed"})
		vectors = ((body or {}).get("result") or {}).get("data") or []
		if len(vectors) != len(texts) or not all(vectors):
			raise Refused(f"{asked[0]} answered {len(vectors)} vectors for {len(texts)} texts", 200, json.dumps(body)[: faults.KEPT])
	except Exception:
		ledger.release(holding)
		raise
	settled = _settled(holding, asked[0], body, caps, money, most, {})
	return {"vectors": vectors, "model": asked[0], "credits": settled["credits"], "metered": settled["metered"]}


def _first_that_answers(asked: list[str], ask):
	"""The first model's answer, or its fallback's when the first cannot
	answer now or no longer exists. A refusal of what was asked is not tried
	again on another model: it would be refused there too."""
	for at, model in enumerate(asked):
		try:
			return model, ask(model)
		except Refused as raised:
			gone = raised.status in (402, 404, 410)
			if at == len(asked) - 1 or not (isinstance(raised, Again) or gone):
				raise
	raise Refused("no model answered")


def _ceiling(asked: list[str], caps: dict, money: dict) -> float:
	"""The most a round could cost on the dearest model it may land on."""
	most = 0.0
	for model in asked:
		try:
			most = max(most, pricing.ceiling(models.rates(model), caps, money["markup"], money["per_dollar"]).credits)
		except pricing.Unpriceable as raised:
			raise Refused(f"{model} cannot be priced: {raised}") from raised
	return most


def _settled(holding: str, model: str, body: dict, caps: dict, money: dict, most: float, out: dict) -> dict:
	"""Charge what the model that answered reported, at its own price; the
	hold where it reported nothing that could be priced."""
	used, unmetered = meter.read(model, body, pricing.asked(caps))
	spent = pricing.bill(models.rates(model, on=date.today().isoformat()), used, money["markup"], money["per_dollar"])
	if unmetered or not spent.whole or not used:
		charged = max(most, _LEAST)
		ledger.commit(holding, charged, spent.usd, model=model)
		return {**out, "credits": charged, "usd": spent.usd, "metered": False, "why": unmetered or _unpriced(spent)}
	ledger.commit(holding, spent.credits, spent.usd, model=model)
	return {
		**out,
		"credits": spent.credits,
		"usd": spent.usd,
		"metered": True,
		"used": [{"kind": u.kind, "modality": u.modality, "unit": u.unit, "count": u.count, "asked": u.asked} for u in used],
	}


_LEAST = 0.000001


def _money() -> dict:
	stored = frappe.get_cached_doc("One Admin Settings")
	return {"markup": stored.default_markup or 0, "per_dollar": stored.credits_per_dollar or 0}


def _unpriced(spent: pricing.Bill) -> str:
	said = ", ".join(f"{u.count} {u.unit} of {u.kind} {u.modality}" for u in spent.unpriced)
	return f"one_ai/models.py prices none of {said}" if said else ""


SAY_IT = "Answer the question above now, in its language. Call a tool if you need one."

ONE_LINE = (
	"A tool call you just wrote could not be read, so it is not shown here. Write it again from the start "
	"with every argument on one line: plain JSON "
	"strings with \\n for a line break, no triple quotes and no code around the call."
)


def _said(
	model: str, turns: list[dict], caps: dict, tenant: str, system: str | None, tools: list[dict] | None, tags: dict, think: bool = False
) -> tuple[str, list[dict], dict]:
	"""The words, what it asked for, and the whole body, asked once more
	when the model wrote a call it could not read or said nothing."""
	if (models.listed().get(model) or {}).get("kind") == "hear":
		return _heard(model, turns, tenant, tags)
	most = int(caps.get("output_tokens") or MOST)
	asking = lambda more=(), fresh=False: talk(  # noqa: E731
		model, [*turns, *more], most=most, tenant=tenant, system=system, tools=tools, fresh=fresh, tags=tags, think=think
	)
	try:
		return asking()
	except faults.Malformed:
		return asking(({"role": "user", "text": ONE_LINE, "calls": []},), fresh=True)
	except faults.Blank as raised:
		if turns and (turns[-1] or {}).get("role") == "tool":
			return "", [], raised.body
		return asking(({"role": "user", "text": SAY_IT, "calls": []},), fresh=True)


def _heard(model: str, turns: list[dict], tenant: str, tags: dict) -> tuple[str, list[dict], dict]:
	"""A recording to text on Whisper, which takes the sound and no
	instruction: each stretch on its own line, after the time it starts."""
	sound = next((one for turn in turns for one in (turn.get("files") or []) if (one.get("type") or "").startswith("audio/")), None)
	if not sound:
		raise Refused(f"{model} was sent nothing to hear")
	body = _run(model, {"audio": sound["data"]}, tenant, tags)
	result = (body or {}).get("result") or {}
	lines = [
		f"[{int(one.get('start') or 0) // 60:02d}:{int(one.get('start') or 0) % 60:02d}] {(one.get('text') or '').strip()}"
		for one in result.get("segments") or []
		if (one.get("text") or "").strip()
	]
	return "\n".join(lines) or (result.get("text") or "").strip(), [], body


def _answered(model: str, answer, words_of, calls_of):
	if answer.status_code != 200:
		raise faults.raised(model, answer.status_code, _detail(answer))
	try:
		body = answer.json()
	except ValueError as raised:
		raise Refused(
			f"{model} answered 200 with something that is not JSON",
			answer.status_code,
			answer.text[: faults.KEPT],
		) from raised

	words = words_of(body)
	wants = calls_of(body)
	if not wants and words and LEAKED in words:
		wants, words = _leaked(words)
	if words is None and not wants and _blank(body):
		empty = faults.Blank(f"{model} answered with nothing in it", 200, json.dumps(body)[: faults.KEPT])
		empty.body = body
		raise empty
	if words is None and not wants and _malformed(body):
		raise faults.Malformed(f"{model} wrote a tool call it could not read", 200, json.dumps(body)[: faults.KEPT])
	if words is None and not wants:
		raise Refused(f"{model} answered 200 with nothing in it", 200, json.dumps(body)[: faults.KEPT])
	return words or "", wants, body


LEAKED = "<|tool_call>"
_CALL = re.compile(r"<\|tool_call>\s*(?:call)?\s*:?\s*([A-Za-z_]\w*)\s*(\{.*?\})\s*<tool_call\|>", re.S)
_QUOTED = re.compile(r'<\|"\|>(.*?)<\|"\|>', re.S)
_KEY = re.compile(r"([{,]\s*)([A-Za-z_]\w*)\s*:")


def _leaked(words: str) -> tuple[list[dict], str]:
	"""The calls Gemma wrote in its own tool-call tokens, and what it said
	around them. Only that syntax, which is a call and nothing else: free-form
	text is never read as one. A call whose arguments do not read is left in
	the words, and nothing is invented."""
	found = []

	def read(match) -> str:
		held = []
		body = _QUOTED.sub(lambda q: held.append(json.dumps(q.group(1))) or f"\x00{len(held) - 1}\x00", match.group(2))
		body = _KEY.sub(lambda k: f'{k.group(1)}"{k.group(2)}":', body)
		body = re.sub(r"\x00(\d+)\x00", lambda n: held[int(n.group(1))], body)
		try:
			args = json.loads(body)
		except ValueError:
			return match.group(0)
		found.append({"id": f"{match.group(1)}-leaked-{len(found)}", "tool": match.group(1), "args": args if isinstance(args, dict) else {}})
		return ""

	rest = _CALL.sub(read, words).strip()
	return found, rest if found else words


def _malformed(body) -> bool:
	"""Gemini's own word for a tool call it wrote and could not read."""
	candidates = (body or {}).get("candidates") if isinstance(body, dict) else None
	return (
		bool(candidates)
		and isinstance(candidates[0], dict)
		and (candidates[0].get("finishReason") == "MALFORMED_FUNCTION_CALL")
	)


def _blank(body) -> bool:
	"""A candidate that finished and carried nothing — Gemini's empty answer.

	Recognised by its shape rather than by "no words": an answer we do not
	understand is still a refusal, so a provider changing its response is not
	silently retried into blanks.
	"""
	candidates = (body or {}).get("candidates") if isinstance(body, dict) else None
	if not candidates or not isinstance(candidates[0], dict):
		return False
	first = candidates[0]
	return first.get("finishReason") == "STOP" and not (first.get("content") or {}).get("parts")


OPENAI_ROLES = {"model": "assistant"}


def _openai_turn(one: dict) -> dict:
	"""Workers AI speaks OpenAI's dialect, where a tool result is its own role."""
	if one.get("role") == "tool":
		return {
			"role": "tool",
			"tool_call_id": one.get("id") or one.get("tool"),
			"content": json.dumps(one.get("result")),
		}
	if one.get("calls"):
		return {
			"role": "assistant",
			"content": one.get("text") or "",
			"tool_calls": [
				{
					"id": call.get("id") or call["tool"],
					"type": "function",
					"function": {"name": call["tool"], "arguments": json.dumps(call.get("args") or {})},
				}
				for call in one["calls"]
			],
		}
	said = one.get("text") or ""
	shown = [one for one in (one.get("files") or []) if one.get("data")]
	role = OPENAI_ROLES.get(one.get("role"), one.get("role") or "user")
	if not shown:
		return {"role": role, "content": said}

	return {
		"role": role,
		"content": [{"type": "text", "text": said}]
		+ [
			{"type": "image_url", "image_url": {"url": f"data:{file['type']};base64,{file['data']}"}}
			for file in shown
		],
	}


def _workers_ai_said(body: dict | None) -> str | None:
	"""Workers AI's words, out of either shape it answers in.

	`result.response` and OpenAI's `result.choices[0].message.content` are both
	read; the thinking is deliberately not read, under either of its names.
	"""
	result = (body or {}).get("result") or body or {}
	if result.get("response") is not None:
		return result["response"]

	choices = result.get("choices") or []
	for choice in choices:
		said = (choice.get("message") or {}).get("content")
		if isinstance(said, str):
			return _without_thinking(said)
		if said is not None:
			return ""
	return "" if choices else None


THINKING = "</think>"
CHANNEL = "<channel|>"


def _without_thinking(said: str) -> str:
	"""The answer, with the model's own thinking taken off the front.

	Only what follows the last close tag, and only when there is one: a model
	that never opened one is left exactly as it wrote.
	"""
	at = said.rfind(THINKING)
	said = said[at + len(THINKING) :].strip() if at != -1 else said
	at = said.rfind(CHANNEL)
	if at != -1:
		return said[at + len(CHANNEL) :].strip()
	return re.sub(r"\A\s*(?:<\|channel>)?:?thought[ \t]*\n", "", said)


def _openai_calls(body: dict | None) -> list[dict]:
	"""What it asked for, out of whichever shape it answered in.

	Workers AI has answered with `result.tool_calls` carrying `name` and an
	`arguments` that is sometimes an object and sometimes a JSON string. Both
	are read, because a provider changing which one it sends is not a thing we
	would find out about in advance.
	"""
	result = (body or {}).get("result") or body or {}
	asked = list(result.get("tool_calls") or [])
	for choice in result.get("choices") or []:
		asked.extend((choice.get("message") or {}).get("tool_calls") or [])

	found = []
	for call in asked:
		named = call.get("function") or call
		called = call.get("id") or named.get("name")
		every = _arguments(named.get("arguments"))
		for n, args in enumerate(every):
			found.append({"id": f"{called}-{n}" if n else called, "tool": named.get("name"), "args": args})
	return [one for one in found if one["tool"]]


def _arguments(args) -> list[dict]:
	"""One call's arguments, or several calls' run together.

	Measured: Gemma 4 asking for two tools of the same name at once comes back
	as one call whose arguments are `{"doctype": "Customer"}{"doctype": "Sales
	Invoice"}`, which `json.loads` refuses, and a tool handed nothing fails.
	"""
	for _ in range(2):
		if not isinstance(args, str):
			break
		every, at, text = [], 0, args.strip()
		while at < len(text):
			try:
				one, at = json.JSONDecoder().raw_decode(text, at)
			except ValueError:
				every = []
				break
			every.append(one)
			while at < len(text) and text[at].isspace():
				at += 1
		if len(every) > 1:
			return [one for one in every if isinstance(one, dict)] or [{}]
		args = every[0] if every else {}
	return [args if isinstance(args, dict) else {}]


# What Gemini 3 is handed back for a call it did not make, such as one a
# conversation's first model made before it was handed on (run.ask):
# measured, without it the request is refused, and with it Gemini answers.
BORROWED = "skip_thought_signature_validator"


def _gemini_turn(one: dict) -> dict:
	"""Google puts a tool result back in the conversation as the user's turn."""
	if one.get("role") == "tool":
		return {
			"role": "user",
			"parts": [
				{
					"functionResponse": {
						"name": one.get("tool"),
						"response": {"result": one.get("result")},
					}
				}
			],
		}
	parts = []
	if one.get("text"):
		parts.append({"text": one["text"]})
	for file in one.get("files") or []:
		if file.get("data"):
			parts.append({"inline_data": {"mime_type": file["type"], "data": file["data"]}})
	for call in one.get("calls") or []:
		said = {"functionCall": {"name": call["tool"], "args": call.get("args") or {}}}
		if one.get("role") == "model":
			said["thoughtSignature"] = call.get("signature") or BORROWED
		parts.append(said)
	return {"role": "model" if one.get("role") == "model" else "user", "parts": parts or [{"text": ""}]}


def _gemini_calls(body: dict | None) -> list[dict]:
	"""What Gemini asked for, and the signature it has to be handed back with.

	Gemini 3 returns a `thoughtSignature` beside every `functionCall` and
	refuses the next request without it: "Function call is missing a
	thought_signature in functionCall parts". It is opaque, it is the model's
	own, and it is carried on our turn only so it can be given back — which is
	why 2.5 works without one and 3.x does not.
	"""
	found = []
	for candidate in (body or {}).get("candidates") or []:
		for part in (candidate.get("content") or {}).get("parts") or []:
			call = part.get("functionCall")
			if call and call.get("name"):
				found.append(
					{
						"id": call.get("id") or call["name"],
						"tool": call["name"],
						"args": call.get("args") or {},
						"signature": part.get("thoughtSignature"),
					}
				)
	return found


def _first_part(body: dict | None) -> str | None:
	"""Gemini's answer, which is nested four deep and may legitimately be empty."""
	for candidate in (body or {}).get("candidates") or []:
		for part in (candidate.get("content") or {}).get("parts") or []:
			if "text" in part:
				return part["text"]
	return None


def _detail(answer) -> str:
	try:
		return faults.detail(answer.json(), answer.text)
	except ValueError:
		return answer.text[: faults.KEPT]


def _settings() -> dict:
	"""Where to call and as whom.

	There is no provider key in here and there is nowhere to put one. A gateway
	that is not configured refuses rather than falling back to calling a
	provider directly, because the fallback is the thing this module exists to
	prevent.
	"""
	stored = frappe.get_cached_doc("One Admin Settings")
	found = {
		"url": frappe.conf.get("ai_gateway_url") or URL,
		"account": frappe.conf.get("cloudflare_account") or stored.cloudflare_account,
		"gateway": frappe.conf.get("ai_gateway") or stored.ai_gateway,
		"token": frappe.conf.get("ai_gateway_token")
		or stored.get_password("ai_gateway_token", raise_exception=False),
	}
	missing = [key for key, value in found.items() if not value]
	if missing:
		raise Refused(
			f"The AI gateway is not configured: {', '.join(sorted(missing))}. Set it in OneAdmin Settings."
		)
	return found
