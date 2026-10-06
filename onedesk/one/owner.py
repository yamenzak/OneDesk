"""A new workspace's first administrator: the person who paid for it.

`hello` names the owner, and a workspace with no administrator yet makes them
one and sends them One's own invitation. Once, and only while nobody
administers it.
"""

import frappe

from onedesk.one import roles


def arrive(said: dict) -> str | None:
	"""Make the owner the admin site names this workspace's first
	administrator, and invite them. The user made, if one was."""
	email = (said.get("owner") or "").strip().lower()
	if not email or not frappe.utils.validate_email_address(email):
		return None
	if roles.administrators() or frappe.db.exists("User", email):
		return None
	roles.ensure()
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": email.split("@", 1)[0],
			"user_type": "System User",
			# One's own invitation instead; frappe's is a reset link that
			# lives twenty minutes.
			"send_welcome_email": 0,
			"roles": [{"role": "Desk User"}, {"role": roles.ADMINISTRATOR}],
		}
	)
	user.insert(ignore_permissions=True)
	from onedesk.one import invite

	invite.send(user.name, inviter="One")
	return user.name
