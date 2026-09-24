"""Files asked of somebody, by name. See one_storage/file_requests.py."""

import hashlib

import frappe
from frappe import _
from frappe.model.document import Document

#: The fields a requested file can fill.
ATTACH = ("Attach", "Attach Image")


def hashed(token: str) -> str:
	return hashlib.sha256(token.encode()).hexdigest()


class CloudFileRequest(Document):
	def validate(self):
		if self.reference_doctype and not frappe.db.exists(self.reference_doctype, self.reference_name):
			frappe.throw(_("{0} {1} is not there.").format(_(self.reference_doctype), self.reference_name))
		if self.folder and not frappe.db.get_value("File", self.folder, "is_folder"):
			frappe.throw(_("Files land in a folder, and {0} is not one.").format(self.folder))
		self._items()
		self._people()

	def _items(self):
		fields = {}
		if self.reference_doctype:
			meta = frappe.get_meta(self.reference_doctype)
			fields = {one.fieldname: one for one in meta.fields if one.fieldtype in ATTACH}
		seen = set()
		for one in self.items:
			one.label = " ".join((one.label or "").replace("/", " ").split())
			if one.label.lower() in seen:
				frappe.throw(_("{0} is asked for twice.").format(one.label))
			seen.add(one.label.lower())
			one.accept = ", ".join(
				ext.strip().lstrip(".").lower() for ext in (one.accept or "").replace(";", ",").split(",") if ext.strip()
			)
			if one.fieldname:
				if not self.reference_doctype:
					frappe.throw(_("{0} fills a record's field, so the request needs a record.").format(one.label))
				if one.fieldname not in fields:
					frappe.throw(_("{0} has no attachment field called {1}.").format(_(self.reference_doctype), one.fieldname))
				one.several = 0

	def _people(self):
		seen, kept = set(), []
		for one in self.recipients:
			one.email = (one.email or "").strip().lower()
			if one.email and one.email not in seen:
				seen.add(one.email)
				kept.append(one)
		self.recipients = kept
		if len(kept) > 1 and any(one.fieldname for one in self.items):
			frappe.throw(_("A request that fills a record's fields goes to one person."))
		self.flags.tokens = self.flags.tokens or {}
		for one in self.recipients:
			if not one.token_hash:
				token = frappe.generate_hash(length=32)
				one.token = token
				one.token_hash = hashed(token)
				self.flags.tokens[one.email] = token
