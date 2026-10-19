"""What every step of the import shares: the company it books into, the map
from old records to new ones that makes it safe to run again, and the notes
it leaves for Rua's accountant."""

import json

import frappe
from frappe.utils import flt

MAP = "Rua Import Record"


class Run:
	def __init__(self, source):
		self.source = source
		self.company = frappe.db.get_default("company")
		self.abbr = frappe.db.get_value("Company", self.company, "abbr")
		self.currency = frappe.db.get_value("Company", self.company, "default_currency")
		self.made_now = {}
		self.notes = []
		self._map = {}
		for row in frappe.get_all(
			MAP, fields=["source_doctype", "source_name", "target_doctype", "target_name"], limit=0
		):
			self._map[(row.source_doctype, row.source_name, row.target_doctype)] = row.target_name

	def docs(self, doctype):
		return self.source.docs(doctype)

	def made(self, source_doctype, source_name, target_doctype):
		"""What an old record became, when it has been brought over already."""
		name = self._map.get((source_doctype, source_name, target_doctype))
		if name and frappe.db.exists(target_doctype, name):
			return name
		return None

	def remember(self, source_doctype, source_name, target_doctype, target_name):
		frappe.get_doc(
			{
				"doctype": MAP,
				"source_doctype": source_doctype,
				"source_name": source_name,
				"target_doctype": target_doctype,
				"target_name": target_name,
			}
		).db_insert()
		self._map[(source_doctype, source_name, target_doctype)] = target_name
		self.made_now[target_doctype] = self.made_now.get(target_doctype, 0) + 1
		return target_name

	def note(self, kind, doctype, name, said):
		self.notes.append(
			{"kind": kind, "reference_doctype": doctype, "reference_name": name, "note": said[:1000]}
		)

	def account(self, account_name, **filters):
		return frappe.db.get_value(
			"Account", {"company": self.company, "account_name": account_name, "is_group": 0, **filters}
		)


def parsed(value, default=None):
	if isinstance(value, list | dict):
		return value
	try:
		return json.loads(value) if value else default
	except ValueError:
		return default


def money(value):
	return flt(value, 2)


def clean(text):
	return " ".join(str(text or "").split())
