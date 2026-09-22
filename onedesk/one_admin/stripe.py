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

from onedesk.one_admin import faults, signing, signup, site

STRIPE = "https://api.stripe.com/v1"
PATIENCE = 20

#: The only event we act on. Everything else is recorded and ignored, which is
#: deliberate: an endpoint that grows a branch per event type is an endpoint
#: nobody can reason about, and the subscription lifecycle is a separate concern
#: with its own stage.
ACTED_ON = "checkout.session.completed"


def checkout(request: str) -> str:
	"""A Stripe Checkout URL for this request, and the session recorded on it."""
	site.require_admin()
	asked = frappe.get_doc("Account Request", request)
	sold = frappe.get_cached_doc("Offering", asked.offering)
	if not sold.stripe_price:
		frappe.throw(frappe._("{0} has no Stripe price.").format(sold.name))

	made = _post(
		"checkout/sessions",
		{
			"mode": "subscription" if sold.recurring else "payment",
			"line_items[0][price]": sold.stripe_price,
			"line_items[0][quantity]": 1,
			"customer_email": asked.email,
			"client_reference_id": asked.name,
			"metadata[request]": asked.name,
			"success_url": _back_to(asked, "done"),
			"cancel_url": _back_to(asked, "cancelled"),
		},
	)
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

	if event.get("type") != ACTED_ON:
		seen.db_set("handled", 1)
		return {"ignored": event.get("type")}

	request = ((event.get("data") or {}).get("object") or {}).get("client_reference_id")
	try:
		tenant = signup.accept(request)
	except Exception as raised:
		seen.db_set({"error": str(raised)[:500], "request": request})
		raise
	seen.db_set({"handled": 1, "request": request, "error": None})
	return {"tenant": tenant}


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
