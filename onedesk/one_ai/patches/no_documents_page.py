"""What waits on a person is a card in their conversation with the agent
that did it (one_chat/cards.py), and each agent's queue is its tab in
AICenter, so OneAI's Documents page is gone."""

import frappe


def execute():
	if frappe.db.exists("Page", "intake"):
		frappe.delete_doc("Page", "intake", force=True, ignore_permissions=True)
