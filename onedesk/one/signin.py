"""How a person signs in, and where they are signed in: the Sign-in page of Settings.

Nothing here is a copy: frappe already keeps it all, and this reads it the way a
person asks, and mails them when their password changes or a passkey is added.
"""

import hashlib
import json

import frappe
from frappe import _

RECENT = 6

BROWSERS = (
	("Edg/", "Edge"),
	("OPR/", "Opera"),
	("Firefox/", "Firefox"),
	("CriOS/", "Chrome"),
	("Chrome/", "Chrome"),
	("Safari/", "Safari"),
)
SYSTEMS = (
	("iPhone", "iPhone"),
	("iPad", "iPad"),
	("Android", "Android"),
	("Windows", "Windows"),
	("Mac OS X", "Mac"),
	("CrOS", "ChromeOS"),
	("Linux", "Linux"),
)


def device(agent: str | None) -> str:
	"""A user agent as a person says it: "Chrome on Mac". Pure."""
	agent = agent or ""
	browser = next((name for mark, name in BROWSERS if mark in agent), None)
	system = next((name for mark, name in SYSTEMS if mark in agent), None)
	if browser and system:
		return _("{0} on {1}").format(browser, system)
	return browser or system or _("An unknown device")


def key(sid: str) -> str:
	"""A session as the page names it. The page never sees a session id: one
	in the browser is one a script there could read. Pure."""
	return hashlib.sha256(sid.encode()).hexdigest()[:16]


def sessions(user: str | None = None) -> list[dict]:
	"""Where the person is signed in and has not yet been signed out by time,
	one row a device: the device, the address, how many sessions it holds,
	when it was last used, and which is this one."""
	from frappe.sessions import get_expired_threshold

	user = user or frappe.session.user
	rows = frappe.db.sql(
		"""select sid, sessiondata, lastupdate from `tabSessions`
		where user = %s and status = 'Active' and lastupdate > %s order by lastupdate desc""",
		(user, get_expired_threshold()),
		as_dict=True,
	)
	return grouped([_place(row) for row in rows], frappe.session.sid)


def _place(row) -> dict:
	try:
		data = json.loads(row.sessiondata or "{}")
	except ValueError:
		data = {}
	return {
		"sid": row.sid,
		"device": device(data.get("user_agent")),
		"address": data.get("session_ip") or "",
		"last_used": row.lastupdate,
	}


def grouped(places: list[dict], here: str | None) -> list[dict]:
	"""Sessions on the same device from the same address as one row, newest
	first and this device on top. A browser left open, a script or a test
	run each opens one, and a person asks about devices. Pure."""
	rows: dict = {}
	for one in places:
		row = rows.setdefault(
			(one["device"], one["address"]),
			{
				"key": key(f"{one['device']}|{one['address']}"),
				"device": one["device"],
				"address": one["address"],
				"count": 0,
				"last_used": one["last_used"],
				"here": False,
			},
		)
		row["count"] += 1
		row["last_used"] = max(row["last_used"], one["last_used"])
		row["here"] = row["here"] or one["sid"] == here
	out = sorted(rows.values(), key=lambda row: row["last_used"], reverse=True)
	return sorted(out, key=lambda row: not row["here"])


def recent(user: str | None = None) -> list[dict]:
	"""The person's last sign-ins, failed ones too: a failed one they did not
	make is somebody trying their password."""
	rows = frappe.get_all(
		"Activity Log",
		filters={"user": user or frappe.session.user, "operation": "Login"},
		fields=["status", "ip_address", "creation"],
		order_by="creation desc",
		limit=RECENT,
		ignore_permissions=True,
	)
	return [
		{"failed": row.status != "Success", "address": row.ip_address or "", "on": row.creation}
		for row in rows
	]


def facts(user: str | None = None) -> dict:
	"""Everything the Sign-in page shows, and what OneAI reads to answer
	whether the account is safe."""
	from frappe.twofactor import two_factor_is_enabled

	from onedesk.one import devices
	from onedesk.one_hr import own, policy
	from onedesk.one_hr import passkey as keys
	from onedesk.one_hr import signin as passkey_signin

	user = user or frappe.session.user
	employee = own.employee_of()
	return {
		"password_changed": frappe.db.get_value("User", user, "last_password_reset_date"),
		"employee": employee,
		"passkey": bool(keys.held(user)),
		"passkeys": [
			{"label": frappe.db.get_value("Device", one.device, "device_name") or one.label}
			for one in keys.every({"user": user})
		],
		"passkey_signs_in": passkey_signin.offered(),
		"passkey_clocks": bool(employee) and policy.self_service(),
		"add_here": _adds_here(devices.here(), user),
		"two_factor": bool(two_factor_is_enabled(user)),
		"two_factor_method": frappe.get_system_settings("two_factor_method")
		if two_factor_is_enabled(user)
		else None,
		"sessions": sessions(user),
		"recent": recent(user),
	}


@frappe.whitelist(methods=["POST"])
def sign_out(key_of: str) -> int:
	"""A device's sessions end, found by the key the page has; this session
	stays, even when it is on that device."""
	from frappe.sessions import delete_session

	mine = frappe.db.sql(
		"select sid, sessiondata, lastupdate from `tabSessions` where user = %s",
		frappe.session.user,
		as_dict=True,
	)
	ended = 0
	for row in mine:
		one = _place(row)
		if key(f"{one['device']}|{one['address']}") == key_of and row.sid != frappe.session.sid:
			delete_session(row.sid, frappe.session.user, reason="Signed out from Settings")
			ended += 1
	return ended


@frappe.whitelist(allow_guest=True, methods=["POST"])
def update_password(
	new_password: str, logout_all_sessions: int = 0, key: str | None = None, old_password: str | None = None
):
	"""Frappe's own password change (the reset link and Settings alike), then
	the person is told. Named in hooks.py under override_whitelisted_methods."""
	from frappe.core.doctype.user.user import update_password as frappes

	from onedesk.one import invite, tell

	said = frappes(new_password, logout_all_sessions=logout_all_sessions, key=key, old_password=old_password)
	if frappe.local.response.get("http_status_code") != 410 and frappe.session.user != "Guest":
		if not invite.spend(frappe.session.user):
			tell.password_changed(frappe.session.user)
	return said


def _adds_here(at, user: str) -> bool:
	return bool(
		at
		and at.use == "Assigned"
		and at.user == user
		and not frappe.db.exists("Clock Device", {"device": at.name, "user": user, "status": "Active"})
	)


def arrived(login_manager) -> None:
	"""on_session_creation: a sign-in from a device the person has not used
	before is told to them, always mailed. The first sign-in is where they
	start, not a change."""
	user = login_manager.user
	if user in ("Administrator", "Guest") or not getattr(frappe.local, "request", None):
		return
	said = device(frappe.request.headers.get("User-Agent"))
	known = json.loads(frappe.defaults.get_user_default("one_devices", user) or "null")
	if known is not None and said not in known:
		from onedesk.one import tell

		tell.new_sign_in(user)
	if known is None or said not in known:
		frappe.defaults.set_user_default("one_devices", json.dumps([*(known or []), said][-20:]), user)
