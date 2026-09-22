"""Keeping the model list true without anybody typing it.

Providers ship models weekly and re-price them without an announcement. A table
of models and prices maintained by hand is wrong inside a month, and the way you
find out is a margin rather than an error. So it syncs, from two places for two
different kinds of fact:

* **what exists, and what it can do** — each provider's own API;
* **what it costs** — the page each provider publishes, parsed by `prices.py`,
  which has no frappe in it and is read back against a saved copy of each page.

Cloudflare's models are listed from Cloudflare's own API, because the token for
that is one we already hold and it is not a provider secret. Google's are listed
*through the gateway*, which forwards the request and attaches the stored key —
so the catalogue is built without a Google key ever reaching this site.

**The sync never overrules the operator.** It creates rows and refreshes facts.
Whether a model is *offered* is a decision and stays one. The only two decisions
it makes on its own are the ones it has to: a model that stopped being priceable
comes off sale, and a model the provider withdrew is marked gone.
"""

from datetime import date

import frappe
import requests

from onedesk.one_admin import faults, gateway, prices, site
from onedesk.one_admin.faults import Again, Refused

#: Cloudflare's own API, which is not the gateway. Listing models is not a model
#: call and does not belong behind it.
CLOUDFLARE = "https://api.cloudflare.com/client/v4"
TIMEOUT = 30

#: Where each provider publishes what it charges.
PAGES = {
	"workers-ai": "https://developers.cloudflare.com/workers-ai/platform/pricing/",
	"google-ai-studio": "https://ai.google.dev/gemini-api/docs/pricing",
}

#: The parser for each page. Kept beside PAGES rather than inside prices.py so
#: that module stays a thing you hand text to.
READS = {"workers-ai": prices.workers_ai, "google-ai-studio": prices.gemini}

#: What Cloudflare calls a task, and what we call the capability. An action
#: names one of ours and the model picker filters on it, so a task we do not
#: recognise is "Other" and simply never matches an action.
A_TASK = {
	"text generation": "Text Generation",
	"text-to-image": "Image Generation",
	"image-to-image": "Image Generation",
	"image-to-text": "Vision",
	"object detection": "Vision",
	"image classification": "Vision",
	"text embeddings": "Embedding",
	"automatic speech recognition": "Speech",
	"text-to-speech": "Speech",
	"translation": "Text Generation",
	"summarization": "Text Generation",
	"text classification": "Text Generation",
}

#: The same for Google, which says what a model can be *called* with rather than
#: what it does. `generateContent` is the general one and covers vision too, so
#: it is read as text generation and an action wanting vision picks a model a
#: person marked as one.
A_METHOD = {
	"embedcontent": "Embedding",
	"batchembedcontents": "Embedding",
	"predict": "Image Generation",
	"predictlongrunning": "Image Generation",
	"generatecontent": "Text Generation",
	"bidigeneratecontent": "Speech",
}

#: How many models a page of Cloudflare's listing holds.
AT_A_TIME = 100


def nightly() -> None:
	"""Catch up on what the providers did while nobody was looking."""
	for provider in PAGES:
		try:
			sync(provider)
		except Exception:
			# One provider being unreachable is not a reason to leave the other
			# a day stale, and the traceback is in the error log either way.
			frappe.log_error(f"catalogue sync: {provider}")


def sync(provider: str) -> dict:
	"""List, price, and write down what changed."""
	site.require_admin()
	listed = discover(provider)
	read = READS[provider](_page(provider))
	found = _matched(provider, listed, read)

	now = frappe.utils.now()
	touched = {"seen": 0, "priced": 0, "review": 0, "withdrawn": 0}
	for one in listed:
		rates, why = found.get(one["model"], ([], ""))
		_write(provider, one, rates, why, now, touched)

	touched["withdrawn"] = _withdraw(provider, {one["model"] for one in listed})
	return touched


def discover(provider: str) -> list[dict]:
	"""Every model the provider currently lists, as `{model, label, capability}`."""
	site.require_admin()
	if provider == "workers-ai":
		return _cloudflare_models()
	if provider == "google-ai-studio":
		return _google_models()
	raise Refused(f"{provider} is not a provider this catalogue knows")


def _cloudflare_models() -> list[dict]:
	account = frappe.conf.get("cloudflare_account") or frappe.get_cached_doc(
		"One Admin Settings"
	).cloudflare_account
	token = frappe.conf.get("cloudflare_token") or frappe.get_cached_doc(
		"One Admin Settings"
	).get_password("cloudflare_token", raise_exception=False)
	if not account or not token:
		raise Refused("Cloudflare is not configured. Set it in One Admin Settings.")

	where = f"{frappe.conf.get('cloudflare_url') or CLOUDFLARE}/accounts/{account}/ai/models/search"
	found, page = [], 1
	while True:
		body = _asked(where, token, {"per_page": AT_A_TIME, "page": page})
		rows = body.get("result") or []
		for row in rows:
			task = ((row.get("task") or {}).get("name") or "").lower()
			found.append(
				{
					"model": row.get("name") or "",
					"label": (row.get("name") or "").rsplit("/", 1)[-1],
					"capability": A_TASK.get(task, "Other"),
				}
			)
		if len(rows) < AT_A_TIME:
			return [one for one in found if one["model"]]
		page += 1


def _google_models() -> list[dict]:
	body = gateway.get("google-ai-studio", "v1beta/models")
	found = []
	for row in body.get("models") or []:
		named = (row.get("name") or "").split("/")[-1]
		methods = [m.lower() for m in (row.get("supportedGenerationMethods") or [])]
		capability = next((A_METHOD[m] for m in methods if m in A_METHOD), "Other")
		found.append(
			{"model": named, "label": row.get("displayName") or named, "capability": capability}
		)
	return [one for one in found if one["model"]]


def _asked(where: str, token: str, params: dict) -> dict:
	try:
		answer = requests.get(
			where, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=TIMEOUT
		)
	except requests.RequestException as raised:
		raise Again(f"Cloudflare could not be reached: {raised}") from raised
	if answer.status_code != 200:
		raise faults.raised("cloudflare/models", answer.status_code, answer.text[: faults.KEPT])
	return answer.json()


def _page(provider: str) -> str:
	try:
		answer = requests.get(PAGES[provider], timeout=TIMEOUT)
	except requests.RequestException as raised:
		raise Again(f"{provider}'s price page could not be reached: {raised}") from raised
	if answer.status_code != 200:
		raise faults.raised(f"{provider} prices", answer.status_code, answer.text[: faults.KEPT])
	return answer.text


def _matched(
	provider: str, listed: list[dict], read: prices.Read
) -> dict[str, tuple[list[prices.Rate], str]]:
	"""Each listed model's rates, or the wording that stopped it having any.

	Cloudflare's page names a model by the id its API answers with, so there is
	nothing to match. Google's page says "Gemini 3.1 Flash Image (Nano Banana 2)"
	where its API says `gemini-3.1-flash-image`, so both sides go through `fold`
	— which costs nothing on the Cloudflare side and means one lookup rather
	than a branch. A name that still does not match is left unpriced rather than
	guessed at.
	"""
	by_fold = {prices.fold(name): name for name in read.rates}
	stopped: dict[str, list[str]] = {}
	for gap in read.gaps:
		stopped.setdefault(prices.fold(gap.model), []).append(f"{gap.what}: {gap.wording}")

	found = {}
	for one in listed:
		name = by_fold.get(prices.fold(one["model"]))
		if name is None:
			found[one["model"]] = ([], frappe._("No price for this model on the published page."))
			continue
		why = "; ".join(stopped.get(prices.fold(name), []))
		rates = prices.in_effect(read.rates[name], date.today())
		if not rates and not why:
			why = frappe._("The page lists this model and no price in effect today.")
		found[one["model"]] = (rates, why)
	return found


def _write(
	provider: str, one: dict, rates: list[prices.Rate], why: str, now: str, touched: dict
) -> None:
	"""One model's row, created or refreshed, without touching the decision.

	A model that cannot be priced comes off sale, which is the first of the two
	decisions the sync is allowed to make: selling something we cannot bill for
	is worse than not selling it.
	"""
	# The name is the key: a provider's id is unique within that provider and
	# not across them, so neither alone would do.
	key = f"{provider}:{one['model']}"
	held = frappe.db.exists("AI Model", key)
	model = frappe.get_doc("AI Model", key) if held else frappe.new_doc("AI Model")
	if not held:
		model.update({"provider": provider, "model": one["model"], "offered": 0})

	model.label = one.get("label") or one["model"]
	model.capability = one.get("capability") or "Other"
	model.seen_on = now
	model.status = "Priced" if rates and not why else "Needs Review"
	model.why = why or None
	if rates:
		model.set("rates", [_row(rate) for rate in rates])
		model.priced_on = now
	if model.status != "Priced":
		model.offered = 0

	model.flags.ignore_permissions = True
	model.save() if held else model.insert(ignore_permissions=True)
	touched["seen"] += 1
	touched["priced" if model.status == "Priced" else "review"] += 1


def _row(rate: prices.Rate) -> dict:
	return {
		"kind": rate.kind,
		"modality": rate.modality,
		"per": rate.per,
		"unit": rate.unit[:140],
		"usd": rate.usd,
		"starts": rate.starts,
		"ends": rate.ends,
	}


def _withdraw(provider: str, still_listed: set[str]) -> int:
	"""A model the provider stopped listing.

	The second and last decision the sync makes on its own. Not deleted: a row
	somebody was billed against has to stay readable, and a model that comes
	back keeps whatever a person decided about it.
	"""
	gone = 0
	for row in frappe.get_all(
		"AI Model", filters={"provider": provider, "status": ["!=", "Withdrawn"]},
		fields=["name", "model"],
	):
		if row.model in still_listed:
			continue
		frappe.db.set_value(
			"AI Model", row.name, {"status": "Withdrawn", "offered": 0}, update_modified=False
		)
		gone += 1
	return gone
