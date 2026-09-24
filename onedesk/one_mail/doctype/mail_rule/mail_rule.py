"""A rule a mailbox's mail is sorted by. See one_mail/rules.py."""

import frappe
from frappe import _
from frappe.model.document import Document


class MailRule(Document):
	def validate(self):
		if self.move_to and frappe.db.get_value("Mail Folder", self.move_to, "account") != self.account:
			frappe.throw(_("A rule can only move mail to a folder of its own mailbox."))
		if not any((self.from_contains, self.to_contains, self.subject_contains, self.has_attachment)):
			frappe.throw(_("Say which mail the rule is for."))
		if not any((self.move_to, self.mark_read, self.star)):
			frappe.throw(_("Say what the rule does."))
