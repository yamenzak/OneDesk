import json

import frappe
from frappe import _
from frappe.model.document import Document


class DisplaySource(Document):
	def validate(self):
		# A source reads with the access of whoever saved it last
		# (one_display/sources.py), so a colleague can't widen it.
		self.read_as = frappe.session.user if frappe.session.user != "Guest" else self.read_as
		if self.kind in ("Records", "Record"):
			frappe.has_permission(self.ref_doctype, "read", throw=True)
			if frappe.get_meta(self.ref_doctype).istable:
				frappe.throw(_("A child table cannot be used as a source."))
		if self.kind == "Records":
			self.filters = _json(self.filters, list, _("Filters are not valid."))
			if self.aggregate in ("Sum", "Average") and not frappe.get_meta(self.ref_doctype).get_field(self.aggregate_field or ""):
				frappe.throw(_("{0} has no field {1}.").format(_(self.ref_doctype), self.aggregate_field or ""))
		if self.kind == "Report":
			frappe.has_permission("Report", "read", doc=self.report, throw=True)
			self.report_filters = _json(self.report_filters, dict, _("Report filters are not valid."))
		if self.kind == "News" and not self.news_sources:
			frappe.throw(_("Choose the News Sources whose headlines to show."))
		if self.kind == "Weather" and not self.weather_place:
			frappe.throw(_("Choose the place whose weather to show."))
		if self.kind == "Exchange Rates":
			from onedesk.one_display.sources import currencies_in

			named = currencies_in(self.currencies)
			if not named:
				frappe.throw(_("Enter at least one currency."))
			unknown = [one for one in named if not frappe.db.exists("Currency", one)]
			if unknown:
				frappe.throw(_("There is no currency {0}.").format(", ".join(unknown)))
			self.currencies = ", ".join(named)


def _json(text, kind, wrong: str) -> str:
	try:
		said = json.loads(text or ("[]" if kind is list else "{}"))
	except ValueError:
		frappe.throw(wrong)
	if not isinstance(said, kind):
		frappe.throw(wrong)
	return json.dumps(said)
