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

	def on_submit(self):
		from onedesk.one_hr import tell

		tell.letter_issued(self)

	def after_insert(self):
		"""An employee's request reaches HR as a notification, not a search."""
		if set(HR) & set(frappe.get_roles()):
			return
		from onedesk.one_hr import tell

		tell.letter_requested(self)
