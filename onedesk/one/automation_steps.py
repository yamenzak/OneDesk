"""One's own steps for frappe's automation engine (one/automations.py), added
through its `automation_actions` hook.

Tell People tells people through the hub (one/notify.py), as Automation Notice,
and fills a mail template in as the composer does (one/mail_templates.py).
"""

from typing import ClassVar

import frappe
from frappe import _
from frappe.utils.translations import N_
from frappe.automation_engine.actions.base import (
	USER_CONTROL,
	AutomationAction,
	AutomationParamError,
	render_value,
)
from frappe.automation_engine.actions.core import _as_list, resolve_recipients


class TellPeople(AutomationAction):
	action_type = "TellPeople"
	label = N_("Tell People")
	description = N_("Notifies people in One and by email, as each person prefers.")
	params_schema: ClassVar[list] = [
		{
			"fieldname": "recipients",
			"label": N_("Recipients"),
			"fieldtype": "JSON",
			"reqd": 1,
			"control": USER_CONTROL,
			"options_source": "notification_recipients",
		},
		{
			"fieldname": "email_template",
			"label": N_("Mail Template"),
			"fieldtype": "Link",
			"options": "Email Template",
		},
		{"fieldname": "subject", "label": N_("Subject"), "fieldtype": "Data", "templatable": True},
		{"fieldname": "message", "label": N_("Message"), "fieldtype": "Text Editor", "templatable": True},
	]

	def validate(self, params, doctype):
		if not _as_list(params.get("recipients")):
			raise AutomationParamError(_("Choose who to notify"), fieldname="recipients")
		template = params.get("email_template")
		if template and not frappe.db.exists("Email Template", template):
			raise AutomationParamError(
				_("There is no mail template {0}").format(template), fieldname="email_template"
			)
		if not template and not (params.get("subject") or "").strip():
			raise AutomationParamError(_("Give a subject or a mail template"), fieldname="subject")

	def execute(self, doc, params, context):
		from onedesk.one import mail_templates, tell

		people = resolve_recipients(_as_list(params.get("recipients")), doc)
		if not people:
			return _("No one to notify")
		if params.get("email_template"):
			said = mail_templates.filled(params["email_template"], doc)
			subject, message = said["subject"], said["message"]
		else:
			subject = render_value(params.get("subject") or "", doc, context)
			message = render_value(params.get("message") or "", doc, context)
		tell.told_by_automation(people, doc, subject, message)
		return _("Notified {0}").format(", ".join(people))
