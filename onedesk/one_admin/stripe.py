"""Taking the money, and believing the answer only when it is signed.

No `stripe` package. Two calls are needed — make a checkout session, and read a
webhook — and one of them is a form-encoded POST. A dependency that exists to
save writing `requests.post` is a dependency to keep current forever.

The webhook is the dangerous half and it has three guards, in this order:

1. **the signature**, checked in `signing.py`, which has no Frappe in it;
2. **the event id**, which is unique on `Stripe Webhook Event`, so a redelivery
   meets a database index rather than a check somebody has to remember to write;
3. **the request's own state**, since `signup.accept` returns the tenant it
   already made rather than making a second one.

Any one of the three would stop a double provision. All three are here because
Stripe redelivers by design — on a timeout, on a non-2xx, hours later — and the
cost of being wrong is a second site somebody is billed for.

The clock is `time.time()` and not `frappe.utils.now_datetime()`. The latter is
the *site's* local time as a naive datetime, so calling `.timestamp()` on it
reinterprets it as the server's local time and lands an offset out — measured
here at four hours, which refused every real delivery. Stripe's `t` is a Unix
timestamp, so it has to be compared against one.
"""

import json
import time

import frappe
import requests
from frappe.database.database import savepoint

from onedesk.one_admin import faults, lifecycle, signing, signup, site

STRIPE = "https://api.stripe.com/v1"
PATIENCE = 20

#: The event that makes a workspace. Everything else is recorded and ignored.
ACTED_ON = "checkout.session.completed"

#: The two that move a workspace up and down the ladder. A subscription's
#: invoice failing is what starts a fall; one being paid is what ends it.
#:
#: Deliberately these two and no more. Stripe sends dozens of event types and an
#: endpoint that grows a branch per type is an endpoint nobody can reason about.
#: `customer.subscription.deleted` is *not* here on purpose: a subscription
#: cancelled at the end of its period stops paying invoices, and the ladder
#: notices that by itself and carries the customer through the grace period —
#: which is the right way to treat somebody who cancelled, rather than
#: suspending them the same afternoon.
OWED = "invoice.payment_failed"
SETTLED = "invoice.paid"


def checkout(request: str) -> str:
	"""A Stripe Checkout URL for this request, and the session recorded on it."""
	site.require_admin()
	asked = frappe.get_doc("Account Request", request)
	sold = frappe.get_cached_doc("Offering", asked.offering)
	if not sold.stripe_price:
		frappe.throw(frappe._("{0} has no Stripe price.").format(sold.name))

	form = {
		"mode": "subscription" if sold.recurring else "payment",
		"line_items[0][price]": sold.stripe_price,
		"line_items[0][quantity]": 1,
		"customer_email": asked.email,
		"client_reference_id": asked.name,
		"metadata[request]": asked.name,
		"success_url": _back_to(asked, "done"),
		"cancel_url": _back_to(asked, "cancelled"),
	}
	if sold.recurring and sold.trial_days:
		# A trial changes nothing downstream. Stripe still takes the card, still
		# completes the session, and still sends `checkout.session.completed` —
		# the subscription simply starts in `trialing` with a zero invoice. So
		# the workspace is built here exactly as a paid one is, and when the
		# trial ends the first real invoice arrives as `invoice.paid` or
		# `invoice.payment_failed`, which is the ladder we already have.
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

	if kind in (OWED, SETTLED):
		try:
			answer = _ladder(kind, body)
		except Exception as raised:
			seen.db_set("error", str(raised)[:500])
			raise
		seen.db_set({"handled": 1, "error": None})
		return answer

	if kind != ACTED_ON:
		seen.db_set("handled", 1)
		return {"ignored": kind}

	# Two things complete a checkout and they are told apart by what the session
	# carries: a signup names the request it came from, a top-up names the
	# workspace and the pack. Anything else is somebody else's session.
	meta = body.get("metadata") or {}
	if meta.get("pack"):
		from onedesk.one_admin import topup

		try:
			entry = topup.bought(body)
		except Exception as raised:
			seen.db_set("error", str(raised)[:500])
			raise
		seen.db_set({"handled": 1, "error": None})
		return {"tenant": meta.get("tenant"), "entry": entry}

	request = body.get("client_reference_id")
	try:
		tenant = signup.accept(request)
	except Exception as raised:
		seen.db_set({"error": str(raised)[:500], "request": request})
		raise
	_remember_customer(tenant, body)
	seen.db_set({"handled": 1, "request": request, "error": None})
	return {"tenant": tenant}


def checkout_for_credits(tenant: str, pack: str) -> str:
	"""A Stripe Checkout URL for a workspace buying a pack.

	A one-off payment rather than a subscription, and the session carries the
	workspace and the pack in its metadata — which is the only thing the webhook
	has to go on when it comes back, since a top-up has no Account Request
	behind it the way a signup does.
	"""
	site.require_admin()
	sold = frappe.get_cached_doc("Offering", pack)
	if not sold.stripe_price:
		frappe.throw(frappe._("{0} has no Stripe price.").format(sold.name))

	held = frappe.db.get_value(
		"Tenant", tenant, ["owner_email", "stripe_customer", "domain", "primary_domain"],
		as_dict=True,
	)
	back = f"https://{held.primary_domain or held.domain}/app/workspace-account"
	made = _post(
		"checkout/sessions",
		{
			"mode": "payment",
			"line_items[0][price]": sold.stripe_price,
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
	route back to a workspace without this.
	"""
	if not tenant:
		return
	frappe.db.set_value(
		"Tenant",
		tenant,
		{
			"stripe_customer": body.get("customer") or "",
			"stripe_subscription": body.get("subscription") or "",
		},
		update_modified=False,
	)


def _ladder(kind: str, body: dict) -> dict:
	"""An invoice failed or settled, so a workspace moves.

	An invoice for a customer we do not know is not an error. It may be a
	checkout still in flight, whose `checkout.session.completed` has not arrived
	or has arrived and not yet been acted on; answering 200 and ignoring it is
	right, because the alternative is Stripe redelivering forever.
	"""
	customer = body.get("customer")
	slug = (
		frappe.db.get_value("Tenant", {"stripe_customer": customer}, "name")
		if customer
		else None
	)
	if not slug:
		return {"ignored": kind, "customer": customer}

	tenant = frappe.get_doc("Tenant", slug)
	if kind == OWED:
		return {"tenant": slug, "rung": lifecycle.owed(tenant)}
	return {"tenant": slug, "rung": lifecycle.paid(tenant)}


def _remember(event: dict):
	"""Write the event down, find that we already had, or leave it to whoever is.

	The unique index is the idempotency. Catching its refusal is not a fallback
	for a check we forgot — it *is* the check, and it is the only one that holds
	when two redeliveries arrive at once.

	The insert is wrapped in a savepoint rather than caught around a bare
	`rollback()`. A plain rollback undoes the whole request, and measured here it
	undid the *first* delivery's work when the second one arrived before it had
	committed — the second then looked for a row it had just destroyed.

	`None` means another delivery holds this event and has not committed yet.
	The caller answers 200 and does nothing, which is right: the delivery that
	holds it is about to finish, and a second worker racing it is how one
	payment becomes two workspaces.
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


def _post(path: str, form: dict) -> dict:
	try:
		answer = requests.post(
			f"{STRIPE}/{path}",
			data=form,
			auth=(_key(), ""),
			timeout=PATIENCE,
		)
	except requests.RequestException as raised:
		raise faults.Again(f"Stripe could not be reached: {raised}") from raised
	if answer.status_code == 200:
		return answer.json()
	detail = (answer.json().get("error") or {}).get("message", answer.text[:300])
	raise faults.raised(path, answer.status_code, detail)


def _back_to(asked, outcome: str) -> str:
	return f"{frappe.utils.get_url()}/welcome?request={asked.name}&outcome={outcome}"


def _key() -> str:
	return _from_settings("stripe_key", "stripe_secret_key")


def _secret() -> str:
	return _from_settings("stripe_webhook_secret", "stripe_webhook_secret")


def _from_settings(conf_key: str, field: str) -> str:
	stored = frappe.get_cached_doc("One Admin Settings")
	found = frappe.conf.get(conf_key) or stored.get_password(field, raise_exception=False)
	if not found:
		frappe.throw(frappe._("Stripe is not configured. Set it in One Admin Settings."))
	return found
