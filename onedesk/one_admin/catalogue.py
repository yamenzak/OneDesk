"""Keeping the model list true without anybody typing it.

What exists comes from each provider's API, what it costs from the page each
provider publishes (`prices.py`). The sync never overrules the operator.
"""

from datetime import date

import frappe
import requests

from onedesk.one_admin import capability, faults, gateway, prices, site
from onedesk.one_admin.faults import Again, Refused

CLOUDFLARE = "https://api.cloudflare.com/client/v4"
TIMEOUT = 30

PAGES = {
	"workers-ai": "https://developers.cloudflare.com/workers-ai/platform/pricing/",
	"google-ai-studio": "https://ai.google.dev/gemini-api/docs/pricing",
}

READS = {"workers-ai": prices.workers_ai, "google-ai-studio": prices.gemini}

AT_A_TIME = 100


def nightly() -> None:
	"""Catch up on what the providers did while nobody was looking. Only the
	account keeps a catalogue."""
	if not site.is_admin():
		return
	for provider in PAGES:
		try:
			sync(provider)
		except Exception:
			frappe.log_error(f"catalogue sync: {provider}")
	searchable()


def searchable() -> str | None:
	"""Search by meaning needs one embedding model on sale, and it is the one
	kind nobody chooses between: when none is offered, the cheapest one that
	could be priced is put on sale and made the default. Every other model
	still waits for an operator."""
	site.require_admin()
	sold = {"capability": "Embedding", "status": "Priced"}
	if frappe.db.exists("AI Model", {**sold, "offered": 1}):
		return None
	rows = frappe.get_all("AI Model", filters=sold, fields=["name", "input_per_million"])
	rows = [one for one in rows if one.input_per_million]
	if not rows:
		return None
	cheapest = min(rows, key=lambda one: (one.input_per_million, one.name)).name
	frappe.db.set_value("AI Model", cheapest, {"offered": 1, "default_for": "Embedding"})
	return cheapest


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

	touched["withdrawn"] = _withdraw(provider, {one["model"] for one in listed}, touched)
	if touched.get("gone"):
		from onedesk.one_admin import tell

		tell.models_gone(touched["gone"])
	return {key: value for key, value in touched.items() if key != "gone"}


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
		raise Refused("Cloudflare is not configured. Set it in OneAdmin Settings.")

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

	Both sides go through `fold`, so a page's name and an API's id meet; a name
	that still does not match is left unpriced rather than guessed at.
	"""
	stopped: dict[str, list[str]] = {}
	for gap in read.gaps:
		stopped.setdefault(prices.fold(gap.model), []).append(f"{gap.what}: {gap.wording}")

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
			why = frappe._("The page lists this model with no current price.")
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
	key = f"{provider}:{one['model']}"
	held = frappe.db.exists("AI Model", key)
	model = frappe.get_doc("AI Model", key) if held else frappe.new_doc("AI Model")
	if not held:
		model.update({"provider": provider, "model": one["model"], "offered": 0})

	model.label = one.get("label") or one["model"]
	model.seen_on = now

	if model.priced_by_hand:
		model.status = "Priced" if model.rates else "Needs Review"
		model.why = None if model.rates else frappe._("Priced by hand with no rates.")
	else:
		model.status = "Priced" if rates and not why else "Needs Review"
		model.why = why or None
		if rates:
			model.set("rates", [_row(rate) for rate in rates])
			model.priced_on = now
	_what_it_does(model, one, [_rated(row) for row in model.rates or []])
	if model.status != "Priced":
		if model.offered or model.default_for:
			touched.setdefault("gone", []).append(
				{"name": key, "label": model.label, "why": "unpriced", "default_for": model.default_for}
			)
		model.offered = 0
		model.default_for = None

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


def _withdraw(provider: str, still_listed: set[str], touched: dict | None = None) -> int:
	"""A model the provider stopped listing.

	The second and last decision the sync makes on its own. Not deleted: a row
	somebody was billed against has to stay readable, and a model that comes
	back keeps whatever a person decided about it.
	"""
	gone = 0
	for row in frappe.get_all(
		"AI Model", filters={"provider": provider, "status": ["!=", "Withdrawn"]},
		fields=["name", "model", "label", "offered", "default_for"],
	):
		if row.model in still_listed:
			continue
		if touched is not None and (row.offered or row.default_for):
			touched.setdefault("gone", []).append(
				{"name": row.name, "label": row.label, "why": "withdrawn", "default_for": row.default_for}
			)
		frappe.db.set_value(
			"AI Model",
			row.name,
			{"status": "Withdrawn", "offered": 0, "default_for": None, "rank": 3},
			update_modified=False,
		)
		gone += 1
	return gone
