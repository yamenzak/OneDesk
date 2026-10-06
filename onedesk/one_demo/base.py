"""What every step of the demo uses: the company, dates in its year, and the
records it makes, each through the path a person's click takes and each
tagged Demo so they can be found again."""

import frappe
from frappe.desk.doctype.tag.tag import DocTags
from frappe.utils import add_days, getdate, nowdate

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
	"""Tag a record Demo, so it can be told apart and taken away."""
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


def dated(doc, date, field: str = "posting_date"):
	"""A transaction dated in the past, as frappe takes one: its own posting
	time switched on."""
	doc.set(field, date)
	if doc.meta.has_field("set_posting_time"):
		doc.set_posting_time = 1
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
