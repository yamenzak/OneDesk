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
	return make(email)


def make(email: str, first_name: str | None = None, last_name: str | None = None, inviting: bool = True) -> str:
	"""The owner as an administrator of the workspace, with their name, and
	sent One's invitation when they are made and `inviting`; somebody already
	there is named and made an administrator. The setup job's owner
	(one/setup_job.py) and `arrive` both come here."""
	roles.ensure()
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
		changed = bool(first_name) and (user.first_name, user.last_name or None) != (first_name, last_name or None)
		if changed:
			user.first_name, user.last_name = first_name, last_name
		if roles.ADMINISTRATOR not in {one.role for one in user.roles}:
			user.append("roles", {"role": roles.ADMINISTRATOR})
			changed = True
		if changed:
			user.save(ignore_permissions=True)
		return user.name
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": first_name or email.split("@", 1)[0],
			"last_name": last_name,
			"user_type": "System User",
			"send_welcome_email": 0,
			"roles": [{"role": "Desk User"}, {"role": roles.ADMINISTRATOR}],
		}
	)
	user.insert(ignore_permissions=True)
	if not inviting:
		return user.name
	from onedesk.account_center import invite
	from onedesk.one_mail import addresses

	addresses.ensure_workspace()

	invite.send(user.name, inviter="One")
	return user.name
