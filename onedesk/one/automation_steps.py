"""One's own steps for frappe's automation engine (one/automations.py), added
through its `automation_actions` hook.

Tell People tells people through the hub (one/notify.py), on the bell and by
mail as each chose, as Automation Notice, and fills a mail template in as the
composer does (one/mail_templates.py). Frappe's Send Notification mails past
the hub, and renders a template with only `doc`, so a template that names the
record's fields bare, as the composer and the leave mails need, prints its
tags there.
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
			"label": N_("Who"),
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
		from markupsafe import Markup

		from onedesk.one import mail_templates, notify

		people = resolve_recipients(_as_list(params.get("recipients")), doc)
		if not people:
			return _("No one to notify")
		if params.get("email_template"):
			said = mail_templates.filled(params["email_template"], doc)
			subject, message = said["subject"], said["message"]
		else:
			subject = render_value(params.get("subject") or "", doc, context)
			message = render_value(params.get("message") or "", doc, context)
		notify.notify(
			"Automation Notice",
			people,
			record=(doc.doctype, doc.name) if doc else None,
			subject=frappe.utils.strip_html(subject or ""),
			# The message is the flow's own, or a checked template's: HTML, cleaned.
			message=Markup(frappe.utils.sanitize_html(message or "")),
		)
		return _("Notified {0}").format(", ".join(people))
