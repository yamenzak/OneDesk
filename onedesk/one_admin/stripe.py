"""Taking the money, and believing the answer only when it is signed.

No `stripe` package. The webhook has three guards, in order: the signature
(`signing.py`), the event id (unique on `Stripe Webhook Event`), and the
request's own state. The clock is `time.time()`, a Unix timestamp like Stripe's.
"""

import hashlib
import json
import time

import frappe
import requests
from frappe.database.database import savepoint

from onedesk.one_admin import faults, ladder, lifecycle, signing, signup, site

STRIPE = "https://api.stripe.com/v1"
PATIENCE = 20

ACTED_ON = "checkout.session.completed"

OWED = "invoice.payment_failed"
SETTLED = "invoice.paid"
ENDED = "customer.subscription.deleted"

REFUNDED = "charge.refunded"


def checkout(request: str) -> str:
	"""A Stripe Checkout URL for this request, and the session recorded on it."""
	site.require_admin()
	asked = frappe.get_doc("Account Request", request)
	sold = frappe.get_cached_doc("Offering", asked.offering)

	form = {
		"mode": "subscription" if sold.recurring else "payment",
		"line_items[0][price]": price_for(sold.name),
		"line_items[0][quantity]": 1,
		"customer_email": asked.email,
		"client_reference_id": asked.name,
		"metadata[request]": asked.name,
		"success_url": _back_to(asked, "done"),
		"cancel_url": _back_to(asked, "cancelled"),
	}
	if sold.recurring and sold.trial_days:
		form["subscription_data[trial_period_days]"] = int(sold.trial_days)
	made = _post("checkout/sessions", form)
	asked.db_set({"status": "Paying", "stripe_session": made.get("id")})
	return made.get("url")


@frappe.whitelist(allow_guest=True, methods=["POST"])
def webhook():
	"""Stripe telling us something happened.

	Answers 200 to anything it has already seen and to anything it does not act
	on, because a non-2xx makes Stripe redeliver — and redelivering an event we
	deliberately ignored is a retry loop with no end.
	"""
	site.require_admin()
	raw = frappe.request.get_data()
	try:
		signing.verify(
			raw,
			frappe.get_request_header("Stripe-Signature"),
			_secret(),
			int(time.time()),
		)
	except signing.Unsigned as unsigned:
		raise frappe.AuthenticationError(str(unsigned)) from unsigned

	event = json.loads(raw)
	seen = _remember(event)
	if seen is None or seen.handled:
		return {"seen": True}

	kind = event.get("type")
	body = (event.get("data") or {}).get("object") or {}

	if kind in (OWED, SETTLED, ENDED):
		try:
			answer = _ladder(kind, body)
		except Exception as raised:
			seen.db_set("error", str(raised)[:500])
			raise
		if kind == SETTLED:
			_book("invoiced", body)
		seen.db_set({"handled": 1, "error": None})
		return answer

	if kind == REFUNDED:
		_book("refunded", body)
		seen.db_set("handled", 1)
		return {"refunded": body.get("id")}

	if kind != ACTED_ON:
		seen.db_set("handled", 1)
		return {"ignored": kind}

	meta = body.get("metadata") or {}
	if meta.get("pack"):
		from onedesk.one_admin import topup

		try:
			entry = topup.bought(body)
		except Exception as raised:
			seen.db_set("error", str(raised)[:500])
			raise
		_book("pack_bought", body)
		seen.db_set({"handled": 1, "error": None})
		return {"tenant": meta.get("tenant"), "entry": entry}

	request = body.get("client_reference_id")
	if not request or not frappe.db.exists("Account Request", request):
		seen.db_set({"handled": 1, "error": None})
		return {"ignored": kind, "request": request}
	try:
		tenant = signup.accept(request)
	except signup.NotBuilt as raised:
		seen.db_set({"handled": 1, "error": str(raised)[:500], "request": request})
		return {"failed": request}
	except Exception as raised:
		seen.db_set({"error": str(raised)[:500], "request": request})
		raise
	_remember_customer(tenant, body)
	from onedesk.one_admin import sales

	sales.paid(request, tenant)
	seen.db_set({"handled": 1, "request": request, "error": None})
	return {"tenant": tenant}


def _book(what: str, body: dict) -> None:
	"""Our own books for what Stripe says happened (books.py), never in the
	way of the workspace: a failure is logged, rolled back to here, and
	booked by the nightly catch-up instead."""
	from onedesk.one_admin import books

	mark = "one_books"
	frappe.db.savepoint(mark)
	try:
		getattr(books, what)(body)
		frappe.db.release_savepoint(mark)
	except Exception:
		frappe.db.rollback(save_point=mark)
		frappe.log_error(title=f"Booking {body.get('id')}")


def checkout_for_credits(tenant: str, pack: str) -> str:
	"""A Stripe Checkout URL for a workspace buying a pack.

	A one-off payment rather than a subscription, and the session carries the
	workspace and the pack in its metadata — which is the only thing the webhook
	has to go on when it comes back, since a top-up has no Account Request
	behind it the way a signup does.
	"""
	site.require_admin()
	sold = frappe.get_cached_doc("Offering", pack)
	price = price_for(sold.name)

	held = frappe.db.get_value(
		"Tenant", tenant, ["owner_email", "stripe_customer", "domain", "primary_domain"],
		as_dict=True,
	)
	back = f"https://{held.primary_domain or held.domain}/desk/workspace-settings?section=plan"
	made = _post(
		"checkout/sessions",
		{
			"mode": "payment",
			"line_items[0][price]": price,
			"line_items[0][quantity]": 1,
			"client_reference_id": tenant,
			"metadata[tenant]": tenant,
			"metadata[pack]": sold.name,
			"success_url": f"{back}?bought={sold.name}",
			"cancel_url": back,
			**(
				{"customer": held.stripe_customer}
				if held.stripe_customer
				else {"customer_email": held.owner_email}
			),
		},
	)
	return made.get("url")


def _remember_customer(tenant: str, body: dict) -> None:
	"""Who Stripe thinks this workspace is.

	Written once, at the first completed checkout, because an invoice event
	names a customer and nothing else — there is no request id on it, and no
	route back to a workspace without this. A second checkout never replaces
	what the first wrote.
	"""
	if not tenant:
		return
	held = frappe.db.get_value("Tenant", tenant, ["stripe_customer", "stripe_subscription"], as_dict=True) or {}
	frappe.db.set_value(
		"Tenant",
		tenant,
		{
			"stripe_customer": held.get("stripe_customer") or body.get("customer") or "",
			"stripe_subscription": held.get("stripe_subscription") or body.get("subscription") or "",
		},
		update_modified=False,
	)


def _ladder(kind: str, body: dict) -> dict:
	"""An invoice failed or settled, or a subscription ended, so a workspace moves.

	An event for a customer we do not know is not an error. It may be a
	checkout still in flight, whose `checkout.session.completed` has not arrived
	or has arrived and not yet been acted on; answering 200 and ignoring it is
	right, because the alternative is Stripe redelivering forever.
	"""
	customer = body.get("customer")
	if kind == ENDED:
		found = {"stripe_subscription": body.get("id")} if body.get("id") else None
	else:
		found = {"stripe_customer": customer} if customer else None
	slug = frappe.db.get_value("Tenant", found, "name") if found else None
	if not slug:
		return {"ignored": kind, "customer": customer}

	tenant = frappe.get_doc("Tenant", slug)
	if kind == OWED:
		return {"tenant": slug, "rung": lifecycle.owed(tenant)}
	if kind == ENDED:
		return {"tenant": slug, "rung": lifecycle.ended(tenant)}
	if tenant.status in ("Overdue", "Suspended") and not _settles(tenant, body):
		return {"tenant": slug, "rung": None, "still_owing": True}
	return {"tenant": slug, "rung": lifecycle.paid(tenant)}


def _settles(tenant, body: dict) -> bool:
	"""Whether a paid invoice clears what this workspace owes (ladder.settled):
	its own subscription's, with nothing else of the customer's still open.
	The subscription is on the invoice, or under `parent` since 2025-03-31."""
	paid_for = body.get("subscription") or (
		((body.get("parent") or {}).get("subscription_details") or {}).get("subscription")
	)
	still = _call("get", "invoices", params={"customer": body.get("customer"), "status": "open", "limit": 100})
	unpaid = [one for one in still.get("data") or [] if one.get("id") != body.get("id")]
	return ladder.settled(paid_for, tenant.get("stripe_subscription"), len(unpaid))


def _remember(event: dict):
	"""Write the event down, find that we already had, or leave it to whoever is.

	The unique index is the idempotency, and the insert is wrapped in a savepoint.
	`None` means another delivery holds this event and has not committed yet.
	"""
	held = frappe.db.exists("Stripe Webhook Event", event.get("id"))
	if held:
		return frappe.get_doc("Stripe Webhook Event", held)

	try:
		with savepoint(catch=frappe.DuplicateEntryError):
			return frappe.get_doc(
				{
					"doctype": "Stripe Webhook Event",
					"event_id": event.get("id"),
					"kind": event.get("type"),
					"body": frappe.as_json(event)[:100000],
				}
			).insert(ignore_permissions=True)
	except frappe.DuplicateEntryError:
		pass

	held = frappe.db.exists("Stripe Webhook Event", event.get("id"))
	return frappe.get_doc("Stripe Webhook Event", held) if held else None


PRORATED = {"proration_behavior": "always_invoice", "payment_behavior": "error_if_incomplete"}


def price_for(offering: str) -> str:
	"""The Stripe price an offering is sold at, made the first time it is sold.

	Made rather than typed: a price id pasted by hand is a price that can say
	one amount on the price list and charge another. A price in Stripe cannot
	be changed, so an offering whose amount changes gets a new one the next
	time it is sold (Offering clears the id when the amount changes).
	"""
	site.require_admin()
	sold = frappe.get_doc("Offering", offering)
	if sold.stripe_price:
		return sold.stripe_price
	form = {
		"product_data[name]": sold.label,
		"unit_amount": round(float(sold.amount) * 100),
		"currency": (sold.currency or "USD").lower(),
		"metadata[offering]": sold.name,
	}
	if sold.recurring:
		form["recurring[interval]"] = "month"
	made = _post("prices", form)
	frappe.db.set_value("Offering", sold.name, "stripe_price", made.get("id"), update_modified=False)
	return made.get("id")


def subscription(sub: str) -> dict:
	return _get(f"subscriptions/{sub}")


def swap_plan(sub: str, old_price: str | None, new_price: str) -> dict:
	"""Move a subscription's plan item to another plan's price, prorated.

	The plan item is the one on the old plan's price, or failing that the one
	no add-on is billed on: a subscription carries one plan and any number of
	add-ons, and only the plan moves here.
	"""
	held = subscription(sub)
	items = ((held.get("items") or {}).get("data")) or []
	add_ons = set(frappe.get_all("Tenant Add-on", filters={"stripe_item": ["is", "set"]}, pluck="stripe_item"))
	plan_item = next((one for one in items if (one.get("price") or {}).get("id") == old_price), None) or next(
		(one for one in items if one.get("id") not in add_ons), None
	)
	if not plan_item:
		raise faults.Refused(f"{sub} has no plan to change")
	return _post(
		f"subscriptions/{sub}",
		{"items[0][id]": plan_item["id"], "items[0][price]": new_price, **PRORATED},
	)


def set_item(sub: str, item: str | None, price: str, quantity: int) -> str | None:
	"""Put an add-on on the subscription at this quantity, prorated: add it,
	change how many, or take it off at zero. Returns the item's id."""
	if quantity <= 0:
		if item:
			_delete(f"subscription_items/{item}", {"proration_behavior": "always_invoice"})
		return None
	if item:
		return _post(f"subscription_items/{item}", {"quantity": quantity, **PRORATED}).get("id")
	return _post(
		"subscription_items",
		{"subscription": sub, "price": price, "quantity": quantity, **PRORATED},
	).get("id")


MADE_BY_POST = ("checkout/sessions", "prices", "subscription_items", "billing_portal/configurations")

ONCE_MINUTES = 10


def _post(path: str, form: dict) -> dict:
	"""A POST that makes something carries an Idempotency-Key of what it asks
	and the ten minutes it is asked in: a retry after a lost answer gets the
	first answer rather than a second thing."""
	if path not in MADE_BY_POST:
		return _call("post", path, data=form)
	asked = json.dumps([path, form, int(time.time() // (ONCE_MINUTES * 60))], sort_keys=True, default=str)
	return _call("post", path, data=form, headers={"Idempotency-Key": hashlib.sha256(asked.encode()).hexdigest()})


def _get(path: str) -> dict:
	return _call("get", path)


PORTAL = "one-portal-1"


def portal(customer: str, back: str) -> str:
	"""A billing portal session for a customer: Stripe's own page for their
	card, billing address and receipts, coming back to `back`."""
	site.require_admin()
	return _post(
		"billing_portal/sessions", {"customer": customer, "return_url": back, "configuration": _portal()}
	).get("url")


def _portal() -> str:
	"""The portal as One allows it, whatever the account's default says: no
	cancelling and no plan change there, which would bypass billing.take and
	closing.ask. Found by its metadata, or made once."""
	held = _call("get", "billing_portal/configurations", params={"active": "true", "limit": 100})
	found = next((one for one in held.get("data") or [] if (one.get("metadata") or {}).get("one") == PORTAL), None)
	if found:
		return found["id"]
	return _post(
		"billing_portal/configurations",
		{
			"metadata[one]": PORTAL,
			"features[payment_method_update][enabled]": "true",
			"features[invoice_history][enabled]": "true",
			"features[customer_update][enabled]": "true",
			"features[customer_update][allowed_updates][0]": "address",
			"features[customer_update][allowed_updates][1]": "name",
			"features[customer_update][allowed_updates][2]": "tax_id",
			"features[subscription_cancel][enabled]": "false",
			"features[subscription_update][enabled]": "false",
		},
	).get("id")


def fetch(path: str, params: dict | None = None) -> dict:
	"""Read one Stripe object or list, for the books (books.py)."""
	site.require_admin()
	return _call("get", path, params=params or {})


def cancel(sub: str) -> None:
	"""Cancel a subscription now (steps.stop_billing). One already cancelled,
	or never there, is the answer wanted, not an error."""
	try:
		_delete(f"subscriptions/{sub}")
	except faults.Refused as refused:
		said = str(refused)
		if "No such subscription" in said or "resource_missing" in said or "canceled" in said:
			return
		raise


def at_period_end(sub: str, ends: bool) -> dict:
	"""End a subscription when its period does, or let it renew again
	(closing.py). Nothing is charged or refunded either way."""
	return _post(f"subscriptions/{sub}", {"cancel_at_period_end": "true" if ends else "false"})


def _delete(path: str, form: dict | None = None) -> dict:
	return _call("delete", path, params=form or {})


def _call(way: str, path: str, **kwargs) -> dict:
	try:
		answer = getattr(requests, way)(
			f"{_base()}/{path}",
			auth=(_key(), ""),
			timeout=PATIENCE,
			**kwargs,
		)
	except requests.RequestException as raised:
		raise faults.Again(f"Stripe could not be reached: {raised}") from raised
	if answer.status_code == 200:
		return answer.json()
	try:
		detail = (answer.json().get("error") or {}).get("message", answer.text[:300])
	except ValueError:
		detail = answer.text[:300]
	raise faults.raised(path, answer.status_code, detail)


def _base() -> str:
	"""Stripe's API, or a stand-in a developer names in site_config as
	`stripe_url`, the way `press_url` names press."""
	return (frappe.conf.get("stripe_url") or STRIPE).rstrip("/")


def _back_to(asked, outcome: str) -> str:
	return f"{frappe.utils.get_url()}/welcome?request={asked.name}&key={asked.access_key}&outcome={outcome}"


def _key() -> str:
	return _from_settings("stripe_key", "stripe_secret_key")


def _secret() -> str:
	return _from_settings("stripe_webhook_secret", "stripe_webhook_secret")


def _from_settings(conf_key: str, field: str) -> str:
	stored = frappe.get_cached_doc("One Admin Settings")
	found = frappe.conf.get(conf_key) or stored.get_password(field, raise_exception=False)
	if not found:
		frappe.throw(frappe._("Stripe is not configured. Set it in OneAdmin Settings."))
	return found
