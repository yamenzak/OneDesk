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

from onedesk.one_admin import capability, faults, gateway, prices, site
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
			produces, reads = capability.A_TASK.get(task, ("", set()))
			found.append(
				{
					"model": row.get("name") or "",
					"label": (row.get("name") or "").rsplit("/", 1)[-1],
					"produces": produces,
					"reads": set(reads),
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
		produces, reads = next((capability.A_METHOD[m] for m in methods if m in capability.A_METHOD), ("", set()))
		found.append(
			{
				"model": named,
				"label": row.get("displayName") or named,
				"produces": produces,
				"reads": set(reads),
			}
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
	stopped: dict[str, list[str]] = {}
	for gap in read.gaps:
		stopped.setdefault(prices.fold(gap.model), []).append(f"{gap.what}: {gap.wording}")

	# Gap models as well as priced ones. A model the page prices in a way this
	# cannot read — Veo, per second of video and by resolution — would otherwise
	# be told "no price on the published page", which is the wrong sentence: the
	# price is there and we could not read it, and those are different problems
	# with different answers.
	by_fold = {prices.fold(name): name for name in read.rates}
	for gap in read.gaps:
		by_fold.setdefault(prices.fold(gap.model), gap.model)
	by_fold.pop("", None)

	found = {}
	for one in listed:
		name = by_fold.get(prices.fold(one["model"]))
		if name is None:
			found[one["model"]] = ([], frappe._("No price for this model on the published page."))
			continue
		why = "; ".join(stopped.get(prices.fold(name), []))
		rates = prices.in_effect(read.rates.get(name) or [], date.today())
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
	model.seen_on = now

	if model.priced_by_hand:
		# A price somebody typed off the provider's page, for a model this
		# cannot read — Veo's per-second video prices differ by resolution and
		# Lyria's are per song. The sync leaves those rows alone rather than
		# deleting a decision every night, and still refreshes everything else.
		model.status = "Priced" if model.rates else "Needs Review"
		model.why = None if model.rates else frappe._("Priced by hand, and no rate has been added.")
	else:
		model.status = "Priced" if rates and not why else "Needs Review"
		model.why = why or None
		if rates:
			model.set("rates", [_row(rate) for rate in rates])
			model.priced_on = now
	# After the rates are settled, so a hand-typed one counts: an output rate for
	# a song is the plainest statement there is that a model makes audio, and it
	# is the only statement Google's API gives us for Lyria at all.
	_what_it_does(model, one, [_rated(row) for row in model.rates or []])
	if model.status != "Priced":
		model.offered = 0

	# A provider may reclassify a model — Cloudflare moved llama-3.2-11b-vision
	# from Vision to Text Generation — and a default it still carries then names
	# something it can no longer do. The default goes rather than the sync
	# stopping, because a nightly job that a validation halts is a catalogue
	# that silently stops updating.
	if model.default_for and not capability.able(model.capability, model.default_for):
		touched.setdefault("undefaulted", []).append(f"{key} ({model.default_for})")
		model.default_for = None

	model.flags.ignore_permissions = True
	model.save() if held else model.insert(ignore_permissions=True)
	touched["seen"] += 1
	touched["priced" if model.status == "Priced" else "review"] += 1


def _what_it_does(model, one: dict, rates: list[prices.Rate]) -> None:
	"""What a model reads and what it makes, from both sources at once.

	The provider's own word sets a floor and the published rates raise it: a
	model priced for image input reads images whatever its API said it was for.
	Which is how `gemini-2.5-flash-lite` stops being "text generation" and
	starts being a model that reads text, images, audio and video.
	"""
	reads = set(one.get("reads") or ())
	reads |= {rate.modality for rate in rates if rate.kind in ("input", "cached")}
	makes = {rate.modality for rate in rates if rate.kind == "output"}

	produces = one.get("produces") or ""
	# An output rate for something other than text is the provider saying what
	# this model is for more plainly than its API did.
	louder = makes - {"text", "other"}
	if len(louder) == 1:
		produces = louder.pop()
	elif not produces and makes:
		produces = "text"

	model.capability = capability.named(produces, reads)
	for one_of in ("text", "image", "audio", "video"):
		model.set(f"reads_{one_of}", 1 if one_of in reads else 0)


def _rated(row) -> prices.Rate:
	"""A stored rate read back as the thing `prices.py` deals in."""
	return prices.Rate(
		kind=row.kind, modality=row.modality, unit=row.unit, per=row.per or 1, usd=row.usd or 0
	)


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
		# The default goes with it. A withdrawn model that is still the default
		# for a capability is a default nothing can replace — every attempt is
		# refused because the old one still holds the name — and the first call
		# that needs it fails with "not offered" rather than with anything that
		# says why.
		frappe.db.set_value(
			"AI Model",
			row.name,
			{"status": "Withdrawn", "offered": 0, "default_for": None},
			update_modified=False,
		)
		gone += 1
	return gone
