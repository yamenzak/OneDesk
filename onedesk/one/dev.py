"""Whether this is a dev site: marked `one_dev` (deploy/local/public.sh) or in
developer mode. What only a dev site offers asks here: the demo company, the
review stamps. And what kind of site this is, for the frame's band: a
training copy (OneAdmin's sessions write `one_copy_ends`), a dev site, or
live."""

import frappe

COPY = "copy"
DEV = "dev"
LIVE = "live"


def site() -> bool:
	return bool(frappe.conf.get("developer_mode") or frappe.conf.get("one_dev"))


def kind(conf) -> dict:
	"""What kind of site a site config says this is: a training copy with the
	day it ends, a dev site, or live. A copy wins over dev, since a session
	from the demo is marked both. Pure."""
	ends = conf.get("one_copy_ends")
	if ends:
		return {"kind": COPY, "ends": str(ends)[:10]}
	if conf.get("one_dev") or conf.get("developer_mode"):
		return {"kind": DEV}
	return {"kind": LIVE}


def require() -> None:
	"""Refuse on a site that is not a dev site."""
	if not site():
		frappe.throw(frappe._("The demo company is built on dev sites only."), frappe.PermissionError)
