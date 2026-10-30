import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class DisplaySource(Document):
	def validate(self):
		# A source reads with the access of whoever saved it last
		# (one_display/sources.py), so a colleague can't widen it.
		self.read_as = frappe.session.user if frappe.session.user != "Guest" else self.read_as
		if self.kind in ("Records", "Record"):
			frappe.has_permission(self.ref_doctype, "read", throw=True)
			if frappe.get_meta(self.ref_doctype).istable:
				frappe.throw(_("A source reads records, not the rows of a table."))
		if self.kind == "Records":
			self.filters = _json(self.filters, list, _("The filters are not a list."))
			if self.aggregate in ("Sum", "Average") and not frappe.get_meta(self.ref_doctype).get_field(self.aggregate_field or ""):
				frappe.throw(_("{0} has no field {1}.").format(_(self.ref_doctype), self.aggregate_field or ""))
		if self.kind == "Report":
			frappe.has_permission("Report", "read", doc=self.report, throw=True)
			self.report_filters = _json(self.report_filters, dict, _("The report's filters are not a set of values."))
		if self.kind == "Feed" and not (self.feed_url or "").startswith("https://"):
			frappe.throw(_("A feed's address starts with https://."))
		if self.kind == "Weather" and not (-90 <= flt(self.latitude) <= 90 and -180 <= flt(self.longitude) <= 180):
			frappe.throw(_("A latitude is between -90 and 90, and a longitude between -180 and 180."))


def _json(text, kind, wrong: str) -> str:
	try:
		said = json.loads(text or ("[]" if kind is list else "{}"))
	except ValueError:
		frappe.throw(wrong)
	if not isinstance(said, kind):
		frappe.throw(wrong)
	return json.dumps(said)
