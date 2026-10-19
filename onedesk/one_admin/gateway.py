"""Every model call, through one door that holds no provider key.

Calls go to Cloudflare AI Gateway, which stores the provider keys. Nothing on a
tenant site reaches this module. `ask` is the un-metered call; `call` the
billed one, hold, call, settle.
"""

import json
import re

import frappe
import requests

from onedesk.one_admin import faults, ledger, meter, pricing, site
from onedesk.one_admin.faults import Again, Refused

URL = "https://gateway.ai.cloudflare.com/v1"


TIMEOUT = 60

THOUGHT = 110

HEADER = "cf-aig-authorization"

TAG = "cf-aig-metadata"

FRESH = "cf-aig-skip-cache"

PROVIDERS = {
	"workers-ai": {
		"path": lambda model: "v1/chat/completions",
		"talk": lambda model, system, turns, tools, most: {
			"model": model,
			"messages": (
				([{"role": "system", "content": system}] if system else [])
				+ [_openai_turn(one) for one in turns]
			),
			"max_tokens": most,
			**({} if most >= THINKS else {"chat_template_kwargs": {"enable_thinking": False}}),
			**({"tools": [{"type": "function", "function": one} for one in tools]} if tools else {}),
		},
		"said": lambda body: _workers_ai_said(body),
		"calls": lambda body: _openai_calls(body),
	},
	"google-ai-studio": {
		"path": lambda model: f"v1beta/models/{model}:generateContent",
		"talk": lambda model, system, turns, tools, most: {
			"contents": [_gemini_turn(one) for one in turns],
			"generationConfig": {"maxOutputTokens": most},
			**({"systemInstruction": {"parts": [{"text": system}]}} if system else {}),
			**({"tools": [{"functionDeclarations": tools}]} if tools else {}),
		},
		"said": lambda body: _first_part(body),
		"calls": lambda body: _gemini_calls(body),
	},
}

THINKS = 2000

ROUNDS = 8

FIRST = ("workers-ai", "@cf/meta/llama-3.1-8b-instruct")

MOST = 512


def ask(prompt: str, most: int = MOST, tenant: str | None = None) -> str:
	"""One text generation, un-metered, and the words it answered."""
	provider, model = FIRST
	return through(provider, model, [said(prompt)], most=most, tenant=tenant)


def through(
	provider: str,
	model: str,
	turns: list[dict],
	most: int = MOST,
	tenant: str | None = None,
	whole: bool = False,
	system: str | None = None,
	tools: list[dict] | None = None,
	fresh: bool = False,
):
	"""One call. `whole` also hands back the body, which is what carries usage.
	`fresh` asks past the gateway's cache, for a call made again because the
	first answer was no answer. `turns` is the whole conversation in our shape;
	`system` and `tools` go where each provider puts them, never into the words.
	"""
	site.require_admin()
	spoken = PROVIDERS.get(provider)
	if not spoken:
		raise Refused(f"{provider} is not a provider this gateway speaks to")

	settings = _settings()
	where = f"{settings['url'].rstrip('/')}/{settings['account']}/{settings['gateway']}/{provider}/{spoken['path'](model)}"
	headers = {HEADER: f"Bearer {settings['token']}", "Content-Type": "application/json"}
	if tenant:
		headers[TAG] = json.dumps({"tenant": tenant})
	if fresh:
		headers[FRESH] = "true"

	try:
		answer = requests.post(
			where,
			headers=headers,
			data=json.dumps(spoken["talk"](model, system, turns, tools, most)),
			timeout=THOUGHT if most >= THINKS else TIMEOUT,
		)
	except requests.Timeout as raised:
		raise Again(f"{model} timed out") from raised
	except requests.RequestException as raised:
		raise Again(f"{model} could not be reached: {raised}") from raised

	return _answered(model, spoken, answer, whole)


def call(
	model: str,
	prompt: str | None,
	tenant: str,
	caps: dict | None = None,
	reference: str | None = None,
	system: str | None = None,
	turns: list[dict] | None = None,
	tools: list[dict] | None = None,
	action: str | None = None,
) -> dict:
	"""One model call, billed: hold a ceiling, make it, settle the actual.

	Hold first, priced from the caps the caller declared; settle on what the
	provider reported, never on an estimate.
	"""
	site.require_admin()
	sold = _offered(model)
	rates = _rates(sold)
	money = _money()
	markup = sold.markup or money["markup"]
	per_dollar = money["per_dollar"]

	try:
		most = pricing.ceiling(rates, caps or {}, markup, per_dollar)
	except pricing.Unpriceable as raised:
		raise Refused(f"{model} cannot be priced: {raised}") from raised

	spoken = turns or [said(prompt or "")]
	holding = ledger.reserve(tenant, max(most.credits, _LEAST), why=model, reference=reference, action=action)
	try:
		answer, wants, body = _said(sold, spoken, caps or {}, tenant, system, tools)
	except Exception:
		ledger.release(holding)
		raise

	used, unmetered = meter.read(sold.provider, body, pricing.asked(caps or {}))
	spent = pricing.bill(rates, used, markup, per_dollar)
	if unmetered or not spent.whole or not used:
		charged = max(most.credits, _LEAST)
		note = unmetered or _unpriced(spent)
		ledger.commit(holding, charged, spent.usd)
		return {
			"said": answer,
			"wants": wants,
			"credits": charged,
			"usd": spent.usd,
			"metered": False,
			"why": note,
		}

	ledger.commit(holding, spent.credits, spent.usd)
	return {
		"said": answer,
		"wants": wants,
		"credits": spent.credits,
		"usd": spent.usd,
		"metered": True,
		"used": [
			{"kind": u.kind, "modality": u.modality, "unit": u.unit, "count": u.count, "asked": u.asked}
			for u in used
		],
	}


_LEAST = 0.000001


def _offered(model: str):
	sold = frappe.get_cached_doc("AI Model", model)
	if not sold.offered or sold.status != "Priced":
		raise Refused(f"{model} is not offered")
	return sold


def _rates(sold) -> list:
	from onedesk.one_admin.prices import Rate

	return [
		Rate(
			kind=row.kind,
			modality=row.modality,
			unit=row.unit,
			per=row.per or 1,
			usd=row.usd or 0,
		)
		for row in sold.rates or []
	]


def _money() -> dict:
	stored = frappe.get_cached_doc("One Admin Settings")
	return {
		"markup": stored.default_markup or 0,
		"per_dollar": stored.credits_per_dollar or 0,
	}


def _unpriced(spent: pricing.Bill) -> str:
	said = ", ".join(f"{u.count} {u.unit} of {u.kind} {u.modality}" for u in spent.unpriced)
	return f"nothing in the catalogue prices {said}" if said else ""


SAY_IT = "Answer the question above now, in its language. Call a tool if you need one."

ONE_LINE = (
	"A tool call you just wrote could not be read, so it is not shown here. Write it again from the start "
	"with every argument on one line: plain JSON "
	"strings with \\n for a line break, no triple quotes and no code around the call."
)


def _said(
	sold, turns: list[dict], caps: dict, tenant: str, system: str | None, tools: list[dict] | None
) -> tuple[str, list[dict], dict]:
	"""The words, what it asked for, and the whole body — which carries the usage."""
	most = int(caps.get("output_tokens") or MOST)
	asking = lambda said=(), fresh=False: through(  # noqa: E731
		sold.provider,
		sold.model,
		[*turns, *said],
		most=most,
		tenant=tenant,
		whole=True,
		system=system,
		tools=tools,
		fresh=fresh,
	)
	try:
		return asking()
	except faults.Malformed:
		return asking(({"role": "user", "text": ONE_LINE, "calls": []},), fresh=True)
	except faults.Blank as raised:
		if turns and (turns[-1] or {}).get("role") == "tool":
			return "", [], raised.body
		return asking(({"role": "user", "text": SAY_IT, "calls": []},), fresh=True)


def get(provider: str, path: str, timeout: int = TIMEOUT) -> dict:
	"""A plain GET at a provider, through the gateway.

	Which is how the catalogue lists Google's models without a Google key on
	this site: the gateway forwards anything under a provider's prefix and
	attaches the stored key on the way. Cloudflare's own models are listed from
	Cloudflare's API instead, because the token for that is one we already hold
	and it is not a provider secret.
	"""
	site.require_admin()
	if provider not in PROVIDERS:
		raise Refused(f"{provider} is not a provider this gateway speaks to")

	settings = _settings()
	where = f"{settings['url'].rstrip('/')}/{settings['account']}/{settings['gateway']}/{provider}/{path.lstrip('/')}"
	try:
		answer = requests.get(where, headers={HEADER: f"Bearer {settings['token']}"}, timeout=timeout)
	except requests.Timeout as raised:
		raise Again(f"{provider} timed out listing {path}") from raised
	except requests.RequestException as raised:
		raise Again(f"{provider} could not be reached: {raised}") from raised

	if answer.status_code != 200:
		raise faults.raised(f"{provider}/{path}", answer.status_code, _detail(answer))
	try:
		return answer.json()
	except ValueError as raised:
		raise Refused(f"{provider}/{path} answered 200 with something that is not JSON") from raised


def _answered(model: str, spoken: dict, answer, whole: bool = False):
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

	words = spoken["said"](body)
	wants = spoken["calls"](body)
	if not wants and words and LEAKED in words:
		wants, words = _leaked(words)
	if words is None and not wants and _blank(body):
		empty = faults.Blank(f"{model} answered with nothing in it", 200, json.dumps(body)[: faults.KEPT])
		empty.body = body
		raise empty
	if words is None and not wants and _malformed(body):
		raise faults.Malformed(
			f"{model} wrote a tool call it could not read", 200, json.dumps(body)[: faults.KEPT]
		)
	if words is None and not wants:
		raise Refused(f"{model} answered 200 with nothing in it", 200, json.dumps(body)[: faults.KEPT])
	return (words or "", wants, body) if whole else (words or "")


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


def said(text: str, role: str = "user", files: list[dict] | None = None) -> dict:
	"""One turn, in our shape. The only place a turn is built by hand."""
	return {"role": role, "text": text or "", "calls": [], "files": files or []}


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
		if call.get("signature"):
			said["thoughtSignature"] = call["signature"]
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
