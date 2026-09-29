"""A new workspace's first administrator: the person who paid for it.

The admin site builds the site and knows who paid (`Tenant.owner_email`), but
it cannot sign in to the site it built, and it holds only a hash of the token
the site proves itself with. So the workspace asks instead. `hello` names the
owner in its answer, and a workspace that has no administrator yet makes them
one and sends them One's own invitation (one/invite.py), with a link that
works for a week. The admin site's last step of a build asks the new site to
ask at once (`account.wake`), so the invitation leaves as the build finishes
rather than at the next nightly refresh.

Once, and only while nobody administers the workspace: an owner who later
hands it to somebody else is never put back, and nobody who already has an
account is touched.
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
