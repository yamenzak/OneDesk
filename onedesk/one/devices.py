"""Devices: the machines the company owns, and where a passkey may live on
them. A browser is told once which machine it is (`mark`, a long-lived
cookie), and from then on `here` answers it. The one README, Devices, has why.
"""

import hashlib

import frappe
from frappe import _
from frappe.utils import now_datetime

from onedesk.one import roles

#: The cookie a marked browser carries, and how long it lasts: as long as the
#: machine does, near enough.
COOKIE = "one_device"
KEEP_SECONDS = 10 * 365 * 24 * 3600


def _hash(token: str) -> str:
	return hashlib.sha256(token.encode()).hexdigest()


def here():
	"""The active Device this browser was marked as, or None."""
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


@frappe.whitelist(methods=["POST"])
def mark(device: str) -> dict:
	"""This browser is that device. An administrator marks any; the person a
	device is assigned to marks their own, at it."""
	doc = frappe.get_doc("Device", device)
	if not (roles.administers() or (doc.use == "Assigned" and doc.user == frappe.session.user)):
		frappe.throw(_("Only an administrator, or the person it is assigned to, can mark this device."), frappe.PermissionError)
	if doc.status != "Active":
		frappe.throw(_("This device is {0}.").format(_(doc.status)))
	token = frappe.generate_hash(length=40)
	frappe.local.cookie_manager.set_cookie(COOKIE, token, max_age=KEEP_SECONDS, httponly=True)
	request = getattr(frappe.local, "request", None)
	frappe.db.set_value(
		"Device",
		device,
		{
			"token_hash": _hash(token),
			"marked_on": now_datetime(),
			"marked_by": frappe.session.user,
			"user_agent": (request.headers.get("User-Agent") if request else "") or "",
		},
	)
	return {"device": device}


@frappe.whitelist(methods=["POST"])
def lost(device: str) -> dict:
	"""Gone: whoever is signed in on it is signed out, and the passkeys made on
	it stop working. The record stays, as Lost."""
	roles.require()
	from frappe.sessions import delete_session

	frappe.db.set_value("Device", device, {"status": "Lost", "token_hash": None})
	keys = frappe.get_all("Clock Device", filters={"device": device, "status": "Active"}, pluck="name")
	for name in keys:
		frappe.db.set_value("Clock Device", name, "status", "Reset")
	ended = 0
	for sid in _sessions(device):
		user = frappe.db.get_value("Sessions", sid, "user")
		if user:
			delete_session(sid, user, reason="Device marked lost")
			ended += 1
	frappe.cache.delete_value(_sessions_key(device))
	return {"passkeys": len(keys), "sessions": ended}


@frappe.whitelist(methods=["POST"])
def add(device_name: str, use: str, user: str | None = None, asset: str | None = None) -> dict:
	roles.require()
	doc = frappe.get_doc(
		{"doctype": "Device", "device_name": device_name, "use": use, "user": user, "asset": asset}
	).insert()
	return {"device": doc.name}


@frappe.whitelist(methods=["POST"])
def retire(device: str) -> None:
	"""No longer the company's: it stops being anybody's, and its passkeys with
	it. Unlike Lost, nobody is signed out."""
	roles.require()
	frappe.db.set_value("Device", device, {"status": "Retired", "token_hash": None})
	for name in frappe.get_all("Clock Device", filters={"device": device, "status": "Active"}, pluck="name"):
		frappe.db.set_value("Clock Device", name, "status", "Reset")


# ------------------------------------------------------------------ sessions


def _sessions_key(device: str) -> str:
	return f"one-device-sessions:{device}"


def _sessions(device: str) -> list[str]:
	return [one.decode() if isinstance(one, bytes) else one for one in frappe.cache.smembers(_sessions_key(device))]


def signed_in(login_manager) -> None:
	"""on_session_creation: a sign-in on a marked device is remembered against
	it, so Lost can end it."""
	at = here()
	if at and frappe.session.sid:
		frappe.cache.sadd(_sessions_key(at.name), frappe.session.sid)


# ------------------------------------------------------------------ reading


def mine(user: str | None = None) -> list[dict]:
	"""The devices assigned to this person, for their Sign-in page: which is
	this browser, and which already holds their passkey."""
	user = user or frappe.session.user
	at = here()
	held = set(
		frappe.get_all("Clock Device", filters={"user": user, "status": "Active", "device": ["is", "set"]}, pluck="device")
	)
	return [
		{
			"name": one.name,
			"device_name": one.device_name,
			"marked": bool(one.token_hash),
			"here": bool(at and at.name == one.name),
			"passkey": one.name in held,
		}
		for one in frappe.get_all(
			"Device",
			filters={"use": "Assigned", "user": user, "status": "Active"},
			fields=["name", "device_name", "token_hash"],
			ignore_permissions=True,
		)
	]


def for_settings() -> dict:
	"""Settings → Workspace → Devices: the company's machines, then every
	passkey on somebody's own."""
	passkeys = frappe.get_all(
		"Clock Device",
		filters={"status": "Active", "credential_id": ["is", "set"]},
		fields=["name", "user", "label", "device", "registered_on", "last_used", "backed_up"],
		order_by="registered_on desc",
		ignore_permissions=True,
	)
	on = {}
	for one in passkeys:
		if one.device:
			on.setdefault(one.device, []).append(one.user)
	at = here()
	company = [
		{
			**one,
			"holder": frappe.utils.get_fullname(one.user) if one.user else "",
			"marked": bool(one.pop("token_hash")),
			"asset_name": frappe.db.get_value("Asset", one.asset, "asset_name") if one.asset else "",
			"here": bool(at and at.name == one.name),
			"passkeys": len(on.get(one.name, [])),
		}
		for one in frappe.get_all(
			"Device",
			fields=["name", "device_name", "use", "user", "asset", "status", "marked_on", "token_hash"],
			order_by="status asc, device_name asc",
		)
	]
	personal = [
		{
			"name": one.name,
			"user": one.user,
			"person": frappe.utils.get_fullname(one.user) if one.user else "",
			"label": one.label,
			"synced": bool(one.backed_up),
			"registered_on": one.registered_on,
			"last_used": one.last_used,
		}
		for one in passkeys
		if not one.device
	]
	return {"company": company, "personal": personal, "here": at.name if at else None}


@frappe.whitelist(methods=["POST"])
def retire_passkey(passkey: str) -> None:
	"""An administrator retires one person's passkey from the list."""
	roles.require()
	frappe.db.set_value("Clock Device", passkey, "status", "Reset")
