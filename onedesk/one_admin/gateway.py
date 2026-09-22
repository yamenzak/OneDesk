"""Every model call, through one door that holds no provider key.

Calls go to **Cloudflare AI Gateway**, and the thing that makes it worth a
dependency is where the keys live: the provider key is stored *in the gateway*,
so this site holds a gateway token and an account id and nothing that would open
an account at Google or anywhere else. A leaked token here buys somebody our
gateway's rate limit and spend cap, not a provider bill.

What the gateway gives us beyond that, none of which we would otherwise write:
caching, retries, a spend limit that is ours rather than the provider's, and a
per-request log we can tag with the workspace that caused it.

**Nothing on a tenant site ever reaches this module.** A workspace asks admin
through `proxy.py` and admin makes the call, for the same reason a workspace
cannot sign its own storage URL: the credential is the product.

`ask` is the un-metered call and stays: it is how an operator proves a token
works. `call` is the billed one — hold, call, settle — and is the door every
model call for a customer goes through.
"""

import json

import frappe
import requests

from onedesk.one_admin import faults, ledger, meter, pricing, site
from onedesk.one_admin.faults import Again, Refused

#: Cloudflare's own base. Overridable from `site_config` so a developer can
#: point at a stand-in without editing a record a migrate would then ship —
#: the same escape hatch `press.py` has, for the same reason.
URL = "https://gateway.ai.cloudflare.com/v1"

#: Long. A generation is two to forty seconds and a timeout here is a call we
#: paid for and threw away. AI 9 moves this off the web worker entirely.
TIMEOUT = 60

#: The gateway's own authorization header.
#:
#: Deliberately not `Authorization`. That header is the *provider's*, and the
#: whole point of this module is that we never send it: the key sits in the
#: gateway and the gateway attaches it on the way out. If `Authorization` ever
#: appears in this file, the design has been undone.
HEADER = "cf-aig-authorization"

#: Where the gateway's per-request log gets the workspace that caused the call.
TAG = "cf-aig-metadata"

#: How each provider spells a text generation behind the gateway: where it
#: lives, how a prompt goes in, and where the words come back.
#:
#: Data rather than a branch per provider, because these three differ for every
#: provider and an `if` here is how a third one becomes a rewrite. The keys are
#: the gateway's own provider slugs and are not ours to choose.
PROVIDERS = {
	"workers-ai": {
		"path": lambda model: model,
		"talk": lambda system, turns, tools, most: {
			"messages": (
				([{"role": "system", "content": system}] if system else [])
				+ [_openai_turn(one) for one in turns]
			),
			"max_tokens": most,
			**(
				{"tools": [{"type": "function", "function": one} for one in tools]}
				if tools
				else {}
			),
		},
		"said": lambda body: ((body or {}).get("result") or {}).get("response"),
		"calls": lambda body: _openai_calls(body),
	},
	"google-ai-studio": {
		"path": lambda model: f"v1/models/{model}:generateContent",
		"talk": lambda system, turns, tools, most: {
			"contents": [_gemini_turn(one) for one in turns],
			"generationConfig": {"maxOutputTokens": most},
			**({"systemInstruction": {"parts": [{"text": system}]}} if system else {}),
			**({"tools": [{"functionDeclarations": tools}]} if tools else {}),
		},
		"said": lambda body: _first_part(body),
		"calls": lambda body: _gemini_calls(body),
	},
}

#: How many times a model may ask for a tool before the loop stops. Each round
#: is a call and is billed, so this is a cost ceiling as much as it is a guard
#: against a model that keeps asking for the same thing.
ROUNDS = 5

#: The one model this stage calls, and the last time a model is named in this
#: app's code. AI 2's catalogue replaces both of these with a row somebody chose
#: — see the rule in docs/ONEAI.md: an action names a capability, a workspace
#: names a model, and nothing else knows one exists.
FIRST = ("workers-ai", "@cf/meta/llama-3.1-8b-instruct")

#: A ceiling on the answer, so the un-metered call cannot run away before there
#: is a ledger to stop it.
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
):
	"""One call. `whole` also hands back the body, which is what carries usage.

	`turns` is the whole conversation in our shape rather than one prompt: a
	round where a model asked for a tool, was given the result and answers again
	is three turns, and a provider has no memory between calls.

	`system` goes where each provider puts a system instruction rather than
	being glued to the front of the first turn, which is the whole reason an
	action can be told things a workspace cannot take away from it. `tools` is
	the same: declared to the provider as tools, never written into the words,
	so a workspace cannot invent one by typing it.
	"""
	site.require_admin()
	spoken = PROVIDERS.get(provider)
	if not spoken:
		raise Refused(f"{provider} is not a provider this gateway speaks to")

	settings = _settings()
	where = f"{settings['url'].rstrip('/')}/{settings['account']}/{settings['gateway']}/{provider}/{spoken['path'](model)}"
	headers = {HEADER: f"Bearer {settings['token']}", "Content-Type": "application/json"}
	if tenant:
		# So a bill somebody disputes can be read back in Cloudflare's own log
		# rather than only in ours.
		headers[TAG] = json.dumps({"tenant": tenant})

	try:
		answer = requests.post(
			where,
			headers=headers,
			data=json.dumps(spoken["talk"](system, turns, tools, most)),
			timeout=TIMEOUT,
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
) -> dict:
	"""One model call, billed: hold a ceiling, make it, settle the actual.

	**Hold first.** Reading a balance and then calling is a race, and refusing
	after the provider has answered is a call we paid for and then told the
	customer they could not have. The hold is priced from the caps the caller
	declared — a ceiling, not a forecast — and the only thing that matters about
	it is that two calls cannot both spend the last credit.

	**Settle on what the provider reported**, never on an estimate. A response
	that carries no usage at all is charged its hold and flagged, because the
	provider billed us for it either way and charging zero would be a model that
	costs money and earns none.
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
	holding = ledger.reserve(tenant, max(most.credits, _LEAST), why=model, reference=reference)
	try:
		answer, wants, body = _said(sold, spoken, caps or {}, tenant, system, tools)
	except Exception:
		ledger.release(holding)
		raise

	used, unmetered = meter.read(sold.provider, body, pricing.asked(caps or {}))
	spent = pricing.bill(rates, used, markup, per_dollar)
	if unmetered or not spent.whole or not used:
		# Charged the hold, named, and never zero.
		charged = max(most.credits, _LEAST)
		note = unmetered or _unpriced(spent)
		ledger.commit(holding, charged)
		return {
			"said": answer,
			"wants": wants,
			"credits": charged,
			"usd": spent.usd,
			"metered": False,
			"why": note,
		}

	ledger.commit(holding, spent.credits)
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


#: The smallest hold worth taking. A call whose caps price at nothing still has
#: to reserve something, or two of them race for a balance neither is holding.
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


def _said(
	sold, turns: list[dict], caps: dict, tenant: str, system: str | None, tools: list[dict] | None
) -> tuple[str, list[dict], dict]:
	"""The words, what it asked for, and the whole body — which carries the usage."""
	most = int(caps.get("output_tokens") or MOST)
	return through(
		sold.provider,
		sold.model,
		turns,
		most=most,
		tenant=tenant,
		whole=True,
		system=system,
		tools=tools,
	)


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
		answer = requests.get(
			where, headers={HEADER: f"Bearer {settings['token']}"}, timeout=timeout
		)
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
	if words is None and not wants:
		# A 200 with neither words nor a tool call in it is not an empty answer,
		# it is a shape we do not understand — and treating it as an empty
		# answer is how a provider changing its response silently starts
		# returning blanks to customers.
		raise Refused(f"{model} answered 200 with nothing in it", 200, json.dumps(body)[: faults.KEPT])
	return (words or "", wants, body) if whole else (words or "")


# ------------------------------------------------ one conversation, two shapes
#
# A turn of ours is `{role, text, calls}` or `{role: "tool", id, tool, result}`,
# which is neither provider's shape and is deliberately both of theirs written
# down once. The tenant holds the conversation and sends it with each round —
# admin keeps nothing, because admin has no session with a workspace and is not
# going to grow one.


def said(text: str, role: str = "user") -> dict:
	"""One turn, in our shape. The only place a turn is built by hand."""
	return {"role": role, "text": text or "", "calls": []}


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
	return {"role": one.get("role") or "user", "content": one.get("text") or ""}


def _openai_calls(body: dict | None) -> list[dict]:
	"""What it asked for, out of whichever shape it answered in.

	Workers AI has answered with `result.tool_calls` carrying `name` and an
	`arguments` that is sometimes an object and sometimes a JSON string. Both
	are read, because a provider changing which one it sends is not a thing we
	would find out about in advance.
	"""
	result = (body or {}).get("result") or {}
	found = []
	for call in result.get("tool_calls") or []:
		named = call.get("function") or call
		args = named.get("arguments")
		if isinstance(args, str):
			try:
				args = json.loads(args)
			except ValueError:
				args = {}
		found.append(
			{"id": call.get("id") or named.get("name"), "tool": named.get("name"), "args": args or {}}
		)
	return [one for one in found if one["tool"]]


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
	for call in one.get("calls") or []:
		parts.append({"functionCall": {"name": call["tool"], "args": call.get("args") or {}}})
	return {"role": "model" if one.get("role") == "model" else "user", "parts": parts or [{"text": ""}]}


def _gemini_calls(body: dict | None) -> list[dict]:
	found = []
	for candidate in ((body or {}).get("candidates") or []):
		for part in ((candidate.get("content") or {}).get("parts") or []):
			call = part.get("functionCall")
			if call and call.get("name"):
				found.append(
					{"id": call["name"], "tool": call["name"], "args": call.get("args") or {}}
				)
	return found


def _first_part(body: dict | None) -> str | None:
	"""Gemini's answer, which is nested four deep and may legitimately be empty."""
	for candidate in ((body or {}).get("candidates") or []):
		for part in ((candidate.get("content") or {}).get("parts") or []):
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
			f"The AI gateway is not configured: {', '.join(sorted(missing))}. "
			"Set it in One Admin Settings."
		)
	return found
