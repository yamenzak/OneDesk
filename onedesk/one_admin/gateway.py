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

This is the un-metered call. Pricing, the hold and the settle arrive in AI 4;
until then `ask` is one request and one string back, so the gateway is proved
before anything is built on top of it.
"""

import json

import frappe
import requests

from onedesk.one_admin import faults, site
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
		"body": lambda prompt, most: {
			"messages": [{"role": "user", "content": prompt}],
			"max_tokens": most,
		},
		"said": lambda body: ((body or {}).get("result") or {}).get("response"),
	},
	"google-ai-studio": {
		"path": lambda model: f"v1/models/{model}:generateContent",
		"body": lambda prompt, most: {
			"contents": [{"parts": [{"text": prompt}]}],
			"generationConfig": {"maxOutputTokens": most},
		},
		"said": lambda body: _first_part(body),
	},
}

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
	return through(provider, model, prompt, most=most, tenant=tenant)


def through(
	provider: str, model: str, prompt: str, most: int = MOST, tenant: str | None = None
) -> str:
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
			where, headers=headers, data=json.dumps(spoken["body"](prompt, most)), timeout=TIMEOUT
		)
	except requests.Timeout as raised:
		raise Again(f"{model} timed out") from raised
	except requests.RequestException as raised:
		raise Again(f"{model} could not be reached: {raised}") from raised

	return _answered(model, spoken, answer)


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


def _answered(model: str, spoken: dict, answer) -> str:
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

	said = spoken["said"](body)
	if said is None:
		# A 200 with no words in it is not an empty answer, it is a shape we do
		# not understand — and treating it as an empty answer is how a provider
		# changing its response silently starts returning blanks to customers.
		raise Refused(f"{model} answered 200 with no text in it", 200, json.dumps(body)[: faults.KEPT])
	return said


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
