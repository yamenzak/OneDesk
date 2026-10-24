"""A rule a mailbox's mail is sorted by. See one_mail/rules.py."""

import frappe
from frappe import _
from frappe.model.document import Document


class MailRule(Document):
	def validate(self):
		if self.move_to and frappe.db.get_value("Mail Folder", self.move_to, "account") != self.account:
			frappe.throw(_("The folder must be in the rule's mailbox."))
		if not any(
			(
				self.from_contains,
				self.to_contains,
				self.subject_contains,
				self.body_contains,
				self.has_attachment,
				self.about,
			)
		):
			frappe.throw(_("Set at least one condition under When."))
		if self.about and not frappe.db.get_value("Email Account", self.account, "one_intake"):
			frappe.throw(
				_(
					"A rule with About needs Read with OneAI turned on for this mailbox."
				)
			)
		if not any((self.move_to, self.mark_read, self.star, self.reply)):
			frappe.throw(_("Set at least one action under Then."))
		if self.reply and self.reply_with == "OneAI":
			from onedesk.one_mail import gate

			if not self.reply_instruction:
				frappe.throw(_("Write the Instruction for OneAI's reply."))
			if not gate.may_read(self.account):
				frappe.throw(_("OneAI is turned off for this mailbox."))
		elif self.reply and not frappe.utils.strip_html_tags(self.reply_text or "").strip():
			frappe.throw(_("Write the Reply Text."))
