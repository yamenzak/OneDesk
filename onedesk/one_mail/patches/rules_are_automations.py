"""Every Mail Rule becomes an Automation that mail arriving in its mailbox
starts (AutomationCenter, one_mail/blocks.py), keeping its name, so what a
rule already did (a reply sent once per conversation, a record it made, a
topic OneAI reads for) stays its own, its owner, when it was made, its
order, whether it is on and who asked for it. Its steps are kept as they
are: they were already the blocks'. Run again, a rule already moved is
left alone; the table goes with the doctype once migrate finds it orphaned."""

import frappe


def execute():
	from onedesk.one_mail.blocks import ARRIVES

	if not frappe.db.table_exists("Mail Rule") or not frappe.db.table_exists("Automation"):
		return
	moved = set(frappe.get_all("Automation", pluck="name"))
	for row in frappe.db.sql("select * from `tabMail Rule` order by creation asc", as_dict=True):
		if row.name in moved or not row.get("account"):
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Automation",
				"name": row.name,
				"title": row.get("title") or "",
				"enabled": row.get("enabled") or 0,
				"priority": row.get("priority") if row.get("priority") is not None else 10,
				"trigger": ARRIVES,
				"scope_type": "Email Account",
				"scope": row.account,
				"steps": row.get("steps") or "[]",
				"requested_by": row.get("requested_by"),
				"owner": row.owner,
				"creation": row.creation,
				"modified": row.modified,
				"modified_by": row.modified_by,
			}
		)
		doc.db_insert()
