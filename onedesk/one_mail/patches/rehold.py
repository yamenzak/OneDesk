"""Mailboxes back to their holders. Until 5 November 2026 the daily cover
job (rules.cover) deleted every User Email row with no cover date, so each
night every person lost their own address and every shared mailbox its
holders. A person's own address goes back to whoever's Mail Name it carries;
a shared mailbox goes back to who its User history says was given it and not
since taken off. Own addresses go first: saving a person who holds none
makes one (addresses.for_person), and theirs is still there."""

import json

import frappe

from onedesk.one_mail import addresses


def execute():
	hosted = frappe.get_all(
		"Email Account", filters={"one_hosted": 1}, fields=["name", "email_id", "one_shared"], order_by="one_shared asc, name asc"
	)
	for account in hosted:
		if frappe.db.exists("User Email", {"email_account": account.name, "one_cover_until": ["is", "not set"]}):
			continue
		for user in _owner(account) if not account.one_shared else _given(account.name):
			if frappe.db.get_value("User", {"name": user, "enabled": 1, "user_type": "System User"}):
				addresses.hold(account.name, user)


def _owner(account) -> list[str]:
	slug = addresses.slug()
	local = (account.email_id or "").split("@")[0]
	if not slug or not local.endswith(f".{slug}"):
		return []
	return frappe.get_all("User", filters={"one_mail_name": local[: -len(slug) - 1]}, pluck="name", limit=1)


def _given(account: str) -> list[str]:
	held = {}
	for version in frappe.get_all(
		"Version",
		filters={"ref_doctype": "User", "data": ["like", f"%{account}%"]},
		fields=["docname", "data"],
		order_by="creation asc",
	):
		said = json.loads(version.data or "{}")
		for kind, on in (("added", True), ("removed", False)):
			for table, row in said.get(kind) or []:
				if table == "user_emails" and row.get("email_account") == account and not row.get("one_cover_until"):
					held[version.docname] = on
	return [user for user, on in held.items() if on]
