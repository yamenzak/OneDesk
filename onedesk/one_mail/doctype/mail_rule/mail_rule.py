"""A rule a mailbox's mail goes through. See one_mail/flow.py and rules.py."""

import frappe
from frappe import _
from frappe.model.document import Document


class MailRule(Document):
	def validate(self):
		from onedesk.one_mail import flow, gate

		steps = self.steps_of()
		said = flow.problems(steps)
		if said:
			frappe.throw(said[0])
		holders = set(frappe.get_all("User Email", filters={"email_account": self.account}, pluck="parent"))
		for one in flow.actions_in(steps):
			if one.get("type") == "move" and frappe.db.get_value("Mail Folder", one["folder"], "account") != self.account:
				frappe.throw(_("The folder must be in the rule's mailbox."))
			if one.get("type") in ("assign", "notify") and one.get("user") not in holders:
				frappe.throw(_("{0} doesn't use this mailbox.").format(frappe.utils.get_fullname(one.get("user"))))
		uses_ai = flow.needs_ai(steps) or any(
			one.get("type") == "reply" and one.get("with") == "OneAI" for one in flow.actions_in(steps)
		)
		if uses_ai and not gate.may_read(self.account):
			frappe.throw(_("OneAI is turned off for this mailbox."))
		if flow.needs_ai(steps) and self.enabled and not gate.reads(self.account):
			frappe.throw(_("This rule can't run while New Mail is set to Not Read in the mailbox's OneAI tab."))
		self.steps = frappe.as_json(steps, indent=None)
		self.title = (self.title or "").strip() or _("Mail Rule")

	def steps_of(self) -> list:
		said = frappe.parse_json(self.steps) if isinstance(self.steps, str) else self.steps
		return said if isinstance(said, list) else []
