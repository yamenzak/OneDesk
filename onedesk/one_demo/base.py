"""What every step of the demo uses: the company, dates in its year, and the
records it makes, each through the path a person's click takes and each
tagged Demo so they can be found again."""

import frappe
from frappe.desk.doctype.tag.tag import DocTags
from frappe.utils import add_days, flt, getdate, nowdate

TAG = "Demo"

#: The company the demo is, made by the setup wizard.
COMPANY = "Sahara Glass & Aluminium"
ABBR = "SGA"
CURRENCY = "AED"


def today():
	return getdate(nowdate())


def on(month: int, day: int = 1):
	"""A date this year, never after today."""
	date = getdate(f"{today().year}-{month:02d}-{day:02d}")
	return min(date, today())


def ago(days: int):
	return add_days(today(), -days)


def ahead(days: int):
	return add_days(today(), days)


def wh(name: str) -> str:
	"""A warehouse by its short name."""
	return f"{name} - {ABBR}"


def account(name: str) -> str:
	return f"{name} - {ABBR}"


def tag(doc):
	"""Tag a record Demo, so it can be told apart and taken away. The tag is
	the demo's own bookkeeping, not the person's work, so it is added as
	Administrator (frappe asks for write on the record)."""
	with as_user("Administrator"):
		DocTags(doc.doctype).add(doc.name, TAG)
	return doc


def make(values: dict, submit: bool = False):
	"""A record inserted as a form saves it, tagged; submitted when asked."""
	doc = frappe.get_doc(values)
	doc.insert()
	if submit:
		doc.submit()
	return tag(doc)


def save(doc, submit: bool = False):
	"""A record built by a mapper or a One action, saved as a form would."""
	doc.insert()
	if submit:
		doc.submit()
	return tag(doc)


def once(doctype: str, filters, values: dict, submit: bool = False):
	"""The record matching `filters`, made from `values` when there is none."""
	found = frappe.db.exists(doctype, filters)
	if found:
		return frappe.get_doc(doctype, found)
	return make({"doctype": doctype, **values}, submit=submit)


def rated(payment):
	"""A payment in another currency at the rate of its own day. ERPNext
	prices the bank's side at the day's rate when the payment is made, so a
	payment made for a day long gone would be at today's. On submit, the
	difference from the invoice's rate is a gain or a loss in the books."""
	from erpnext.setup.utils import get_exchange_rate

	ours = frappe.get_cached_value("Company", payment.company, "default_currency")
	if payment.payment_type == "Receive" and payment.paid_from_account_currency != ours == payment.paid_to_account_currency:
		rate = get_exchange_rate(payment.paid_from_account_currency, ours, payment.posting_date)
		payment.source_exchange_rate = rate
		payment.received_amount = flt(payment.paid_amount * rate, payment.precision("received_amount"))
	elif payment.payment_type == "Pay" and payment.paid_to_account_currency != ours == payment.paid_from_account_currency:
		rate = get_exchange_rate(payment.paid_to_account_currency, ours, payment.posting_date)
		payment.target_exchange_rate = rate
		payment.paid_amount = flt(payment.received_amount * rate, payment.precision("paid_amount"))
	return payment


def dated(doc, date, field: str = "posting_date"):
	"""A transaction dated in the past, as frappe takes one: its own posting
	time switched on, and in another currency at that day's rate, as ERPNext's
	form fetches it again when the date changes."""
	from erpnext.setup.utils import get_exchange_rate

	doc.set(field, date)
	if doc.meta.has_field("set_posting_time"):
		doc.set_posting_time = 1
	ours = doc.get("company") and frappe.get_cached_value("Company", doc.company, "default_currency")
	if doc.meta.has_field("conversion_rate") and doc.get("currency") and ours and doc.currency != ours:
		doc.conversion_rate = get_exchange_rate(doc.currency, ours, date)
	return doc


def as_user(user: str):
	"""Run what follows as `user`, so what they make is theirs."""
	return _As(user)


class _As:
	def __init__(self, user):
		self.user = user

	def __enter__(self):
		self.was = frappe.session.user
		frappe.set_user(self.user)

	def __exit__(self, *args):
		frappe.set_user(self.was)
