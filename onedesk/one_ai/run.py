"""Asking the account to run an action, from the workspace that wants it.

Two things travel with the call and neither is the instruction: which model this
workspace picked, and what it asked to have added. The instruction itself is the
account's, read from its own copy of the fixture, and there is nothing a
workspace can send that replaces it.

Everything here is one round trip and no decision. Whether the action exists,
whether the model may answer it, whether there are credits — all of that is
admin's, for the same reason a workspace cannot sign its own upload URL.
"""

import frappe

from onedesk.one import account


def ask(action: str, text: str, reference: str | None = None) -> dict:
	"""Run one action on some text and hand back what the model said."""
	chose = mine(action)
	return account.ask(
		"onedesk.one_admin.proxy.ai_run",
		action=action,
		text=text,
		model=chose.get("model") or None,
		extra=chose.get("extra") or None,
		reference=reference,
	)


def mine(action: str) -> dict:
	"""What this workspace has chosen for an action, if anything."""
	held = frappe.db.get_value(
		"AI Action Setting", {"action": action}, ["model", "extra"], as_dict=True
	)
	return dict(held or {})


@frappe.whitelist()
def models(needs: str) -> list[dict]:
	"""The models this workspace may pick, asked of the account.

	Whitelisted so a settings screen can fill a picker. It says nothing about
	prices or credits — only which names may be chosen.
	"""
	frappe.only_for("System Manager")
	return account.ask("onedesk.one_admin.proxy.ai_models", needs=needs) or []


@frappe.whitelist()
def try_it(action: str, text: str) -> dict:
	"""Run an action from the settings screen, so a change can be looked at.

	Charged like any other call, because a preview that is not charged is a
	preview of something else.
	"""
	frappe.only_for("System Manager")
	return ask(action, text, reference=frappe.session.user)
