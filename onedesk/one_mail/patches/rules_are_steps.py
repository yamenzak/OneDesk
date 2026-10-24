"""Mail rules are steps (one_mail/flow.py): each rule of the old shape is
written as steps from its old columns, which stay in the table unread; and a
shared mailbox's Auto Reply that was on becomes a rule that answers new
conversations from outside, once a day to each sender."""

import frappe
from frappe import _


def execute():
	from onedesk.one_mail import flow

	columns = set(frappe.db.get_table_columns("Mail Rule"))
	for row in frappe.db.sql("select * from `tabMail Rule`", as_dict=True):
		if row.get("steps"):
			continue
		steps = flow.from_fields(row) if "from_contains" in columns else []
		when, _then = flow.summary(steps)
		frappe.db.set_value(
			"Mail Rule",
			row.name,
			{"steps": frappe.as_json(steps, indent=None), "title": row.get("title") or when[:140]},
			update_modified=False,
		)
	if "enable_auto_reply" not in set(frappe.db.get_table_columns("Email Account")):
		return
	for account in frappe.get_all(
		"Email Account", filters={"enable_auto_reply": 1, "one_shared": 1}, fields=["name", "auto_reply_message"]
	):
		frappe.get_doc(
			{
				"doctype": "Mail Rule",
				"account": account.name,
				"title": _("Acknowledge New Mail"),
				"priority": 100,
				"steps": frappe.as_json(acknowledge(account.auto_reply_message), indent=None),
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Email Account", account.name, "enable_auto_reply", 0, update_modified=False)


def acknowledge(text: str | None) -> list:
	"""Auto Reply as steps: a new conversation from outside the workspace is
	answered, once a day to each sender."""
	return [
		{
			"type": "if",
			"id": "i1",
			"test": {"any": False, "items": [{"field": "starts", "value": True}, {"field": "outside", "value": True}]},
			"then": [
				{
					"type": "reply",
					"with": "Text",
					"text": (text or "").strip() or _("We received your message and will reply soon."),
					"once": "day",
				}
			],
			"else": [],
		}
	]
