"""The instruction is the account's, and a workspace does not hold a copy.

`AI Action` is a fixture, so a new action arrives with a migrate and every site
gets the row — the label, the capability and the token caps, which is what a
workspace needs to pick a model and add to the prompt. The **instruction** is
not part of that. It is how the product behaves, a workspace cannot change it,
and `proxy.ai_run` has always read it from the account's own copy and ignored
anything sent with the call.

Shipping it and then declining to render it would be a curtain rather than a
wall: the row is in the workspace's database, and `frappe.client.get` reads it.
So on a workspace the field is emptied after every migrate, and there is nothing
to read.
"""

import frappe

from onedesk.one_admin import site


def ready() -> None:
	"""A row per action a workspace may configure, so all of them have a screen.

	Without this the list reads as "two actions" rather than "four, two of which
	somebody has touched" — a setting that only exists once saved is a setting
	nobody knows is there.
	"""
	if site.is_admin():
		return

	for action in frappe.get_all("AI Action", filters={"enabled": 1}, pluck="name"):
		if not frappe.db.exists("AI Action Setting", action):
			frappe.get_doc({"doctype": "AI Action Setting", "action": action}).insert(
				ignore_permissions=True
			)
	frappe.db.commit()


def trim() -> None:
	"""Empty the instruction on a workspace. On the account, leave it alone."""
	if site.is_admin():
		return

	held = frappe.get_all("AI Action", filters={"instruction": ["!=", ""]}, pluck="name")
	for name in held:
		# `db_set` on the row rather than a save: this runs after a migrate has
		# just written the fixture, and a save would fire a validation against a
		# field the migrate is about to write again.
		frappe.db.set_value("AI Action", name, "instruction", "", update_modified=False)
	if held:
		frappe.db.commit()
