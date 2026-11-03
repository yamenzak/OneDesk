"""Whether this is a dev site: marked `one_dev` (deploy/local/public.sh) or in
developer mode. What only a dev site offers asks here: the demo company, the
review stamps."""

import frappe


def site() -> bool:
	return bool(frappe.conf.get("developer_mode") or frappe.conf.get("one_dev"))


def require() -> None:
	"""Refuse on a site that is not a dev site."""
	if not site():
		frappe.throw(frappe._("The demo company is built on dev sites only."), frappe.PermissionError)
