"""Devices: every browser somebody has signed in on, which an administrator
names and sorts into Shared or Assigned. A browser is given an id in a cookie
the first time anybody signs in on it (`signed_in`); `here` answers it after.
"""

import hashlib

import frappe
from frappe.utils import add_days, now_datetime

from onedesk.one import roles

#: The cookie a browser carries, and how long it lasts.
COOKIE = "one_device"
KEEP_SECONDS = 10 * 365 * 24 * 3600

#: An unsorted browser with no passkey, unseen this long, is forgotten.
FORGET_DAYS = 180


def _hash(token: str) -> str:
	return hashlib.sha256(token.encode()).hexdigest()


def here():
	"""The active Device this browser is, or None."""
	request = getattr(frappe.local, "request", None)
	token = request.cookies.get(COOKIE) if request else None
	if not token:
		return None
	found = frappe.get_all(
		"Device",
		filters={"token_hash": _hash(token), "status": "Active"},
		fields=["name", "device_name", "use", "user"],
		limit=1,
		ignore_permissions=True,
	)
	return frappe._dict(found[0]) if found else None


def signed_in(login_manager) -> None:
	"""on_session_creation: the browser gets its id if it has none, and is
	noted as seen, by whom, and from where. The session is remembered against
	it, so Lost can end it."""
	from onedesk.one.signin import device as said

	request = getattr(frappe.local, "request", None)
	if not request or not frappe.session.sid or frappe.session.user in ("Guest", "Administrator"):
		return
	agent = request.headers.get("User-Agent") or ""
	token = request.cookies.get(COOKIE)
	name = token and frappe.db.get_value("Device", {"token_hash": _hash(token)})
	if not name:
		token = frappe.generate_hash(length=40)
		name = (
			frappe.get_doc(
				{"doctype": "Device", "device_name": said(agent), "token_hash": _hash(token), "user_agent": agent}
			)
			.insert(ignore_permissions=True)
			.name
		)
	frappe.local.cookie_manager.set_cookie(COOKIE, token, max_age=KEEP_SECONDS, httponly=True)
	frappe.db.set_value(
		"Device",
		name,
		{
			"last_user": frappe.session.user,
			"last_seen": now_datetime(),
			"last_address": frappe.local.request_ip,
			"user_agent": agent,
		},
		update_modified=False,
	)
	frappe.cache.sadd(_sessions_key(name), frappe.session.sid)


@frappe.whitelist(methods=["POST"])
def save(device: str, device_name: str, use: str | None = None, user: str | None = None, asset: str | None = None) -> dict:
	"""What the administrator says a browser is. Passkeys already on it that
	no longer belong there stop working: everybody's on a shared one, and
	everybody's but its person's on an assigned one."""
	roles.require()
	doc = frappe.get_doc("Device", device)
	doc.update({"device_name": device_name, "use": use or "", "user": user, "asset": asset})
	doc.save()
	if not doc.use:
		return {"retired": 0}
	filters = {"device": device, "status": "Active"}
	if doc.use == "Assigned":
		filters["user"] = ["!=", doc.user]
	keys = frappe.get_all("Clock Device", filters=filters, pluck="name")
	for name in keys:
		frappe.db.set_value("Clock Device", name, "status", "Reset")
	return {"retired": len(keys)}


@frappe.whitelist(methods=["POST"])
def lost(device: str) -> dict:
	"""Whoever is signed in on it is signed out, and its passkeys stop working."""
	roles.require()
	from frappe.sessions import delete_session

	keys = _retire(device, "Lost")
	ended = 0
	for sid in _sessions(device):
		# Sessions is keyed by sid and has no `name`, so get_value cannot read it.
		user = frappe.db.sql("select user from `tabSessions` where sid = %s", sid, pluck=True)
		if user:
			delete_session(sid, user[0], reason="Device marked lost")
			ended += 1
	frappe.cache.delete_value(_sessions_key(device))
	return {"passkeys": keys, "sessions": ended}


@frappe.whitelist(methods=["POST"])
def retire(device: str) -> None:
	"""No longer in use: its passkeys stop working, and nobody is signed out."""
	roles.require()
	_retire(device, "Retired")


def _retire(device: str, status: str) -> int:
	frappe.db.set_value("Device", device, {"status": status, "token_hash": None})
	keys = frappe.get_all("Clock Device", filters={"device": device, "status": "Active"}, pluck="name")
	for name in keys:
		frappe.db.set_value("Clock Device", name, "status", "Reset")
	return len(keys)


def forget() -> None:
	"""Daily: a browser nobody sorted, that holds no passkey and has not been
	seen in half a year, is a private window or cleared data, not a machine."""
	held = set(frappe.get_all("Clock Device", filters={"device": ["is", "set"]}, pluck="device"))
	for name in frappe.get_all(
		"Device",
		filters={"use": ["in", ["", None]], "last_seen": ["<", add_days(now_datetime(), -FORGET_DAYS)]},
		pluck="name",
	):
		if name not in held:
			frappe.delete_doc("Device", name, ignore_permissions=True, force=True)


def _sessions_key(device: str) -> str:
	return f"one-device-sessions:{device}"


def _sessions(device: str) -> list[str]:
	return [one.decode() if isinstance(one, bytes) else one for one in frappe.cache.smembers(_sessions_key(device))]


def for_settings() -> dict:
	"""Settings → Workspace → Devices: sorted ones first, then by last seen."""
	keys = {}
	for one in frappe.get_all("Clock Device", filters={"status": "Active", "device": ["is", "set"]}, pluck="device"):
		keys[one] = keys.get(one, 0) + 1
	at = here()
	rows = [
		{
			**one,
			"holder": frappe.utils.get_fullname(one.user) if one.user else "",
			"seen_by": frappe.utils.get_fullname(one.last_user) if one.last_user else "",
			"asset_name": frappe.db.get_value("Asset", one.asset, "asset_name") if one.asset else "",
			"here": bool(at and at.name == one.name),
			"passkeys": keys.get(one.name, 0),
		}
		for one in frappe.get_all(
			"Device",
			filters={"status": "Active"},
			fields=["name", "device_name", "use", "user", "asset", "last_user", "last_seen", "last_address"],
			order_by="last_seen desc",
		)
	]
	rows.sort(key=lambda one: not one["use"])
	return {"devices": rows}
