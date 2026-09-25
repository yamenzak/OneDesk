"""A letter HR issues about somebody: a salary certificate, an experience letter.

Asked for by the employee — in the OneAI panel, which drafts it from their own
record — or written by HR. A draft is the request; submitting is issuing it,
and only HR may. See `one_hr/ai_letters.py`.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

#: The roles that write letters about anybody. Everybody else writes their own.
HR = ("HR Manager", "HR User")


class EmployeeLetter(Document):
	def validate(self):
		from onedesk.one_hr import own

		if set(HR) & set(frappe.get_roles()):
			return
		if self.employee != own.employee_of():
			frappe.throw(frappe._("You can only ask for a letter about yourself."))

	def before_submit(self):
		self.issued_by = frappe.session.user
		self.issued_on = now_datetime()

	def after_insert(self):
		"""An employee's request reaches HR as a notification, not a search."""
		if set(HR) & set(frappe.get_roles()):
			return
		from onedesk.one import notify

		managers = frappe.get_all(
			"Has Role",
			filters={"role": "HR Manager", "parenttype": "User", "parent": ["not in", ["Administrator", "Guest"]]},
			pluck="parent",
		)
		enabled = frappe.get_all("User", filters={"name": ["in", managers], "enabled": 1}, pluck="name")
		if not enabled:
			return
		notify.notify(
			"Letter Requested",
			enabled,
			record=(self.doctype, self.name),
			employee=self.employee_name,
			kind=frappe._(self.kind).lower(),
		)
