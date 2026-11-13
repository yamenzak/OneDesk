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


def kind(agent: str | None) -> str:
	"""What a user agent is held in: "phone", "tablet" or "computer". Pure."""
	agent = agent or ""
	if "iPad" in agent or "Tablet" in agent or ("Android" in agent and "Mobile" not in agent):
		return "tablet"
	if "Mobile" in agent or "iPhone" in agent or "Android" in agent:
		return "phone"
	return "computer"


def key(sid: str) -> str:
	"""A session as the page names it. The page never sees a session id: one
	in the browser is one a script there could read. Pure."""
	return hashlib.sha256(sid.encode()).hexdigest()[:16]


def hash_sid(sid: str) -> str:
	"""A session id as frappe keeps it in Sessions: hashed, so the table
	never holds one a browser could use."""
	from frappe.sessions import hash_sid as hashed

	return hashed(sid)


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
	return grouped([_place(row) for row in rows], hash_sid(frappe.session.sid))


def _place(row) -> dict:
	try:
		data = json.loads(row.sessiondata or "{}")
	except ValueError:
		data = {}
	return {
		"sid": row.sid,
		"device": device(data.get("user_agent")),
		"kind": kind(data.get("user_agent")),
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
				"kind": one.get("kind", "computer"),
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
	from frappe.twofactor import get_default, two_factor_is_enabled

	from onedesk.account_center import devices
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
		"two_factor_ready": bool(get_default(user + "_otplogin")),
		"sessions": sessions(user),
		"recent": recent(user),
	}


def way_in(user: str) -> str:
	"""How a person signs in, at its strongest: "passkey", "two_factor" (on and
	set up), "two_factor_pending" (asked for, not set up yet) or "password"."""
	from frappe.twofactor import get_default, two_factor_is_enabled

	from onedesk.one_hr import passkey as keys

	if keys.held(user):
		return "passkey"
	if two_factor_is_enabled(user):
		return "two_factor" if get_default(user + "_otplogin") else "two_factor_pending"
	return "password"


def warnings(said: dict) -> list[str]:
	"""What is weak about how the person signs in, in plain words, worst
	first: somebody else trying their password, then a password that has
	never changed with no passkey beside it. Pure."""
	out = []
	failed = [one for one in said["recent"] if one["failed"]]
	if failed:
		out.append(
			_("Someone got your password wrong {0} times, last {1}. If it wasn't you, change your password.").format(
				len(failed), frappe.utils.pretty_date(failed[0]["on"])
			)
			if len(failed) > 1
			else _("Someone got your password wrong {0}. If it wasn't you, change your password.").format(frappe.utils.pretty_date(failed[0]["on"]))
		)
	if not said["password_changed"] and not said["passkey"]:
		out.append(_("Your password has never been changed and you have no passkey."))
	return out


@frappe.whitelist(methods=["POST"])
def reset_two_factor() -> None:
	"""The person's own authenticator forgotten, for a new phone."""
	forget_two_factor(frappe.session.user)


def forget_two_factor(user: str) -> None:
	"""A person's authenticator forgotten: they scan a new code the next time
	they sign in, and are told it happened. What frappe's reset_otp_secret
	clears, without its mail, whose job frappe enqueues with an argument rq
	refuses."""
	from frappe.twofactor import clear_default

	from onedesk.one import tell

	if not frappe.db.get_single_value("System Settings", "enable_two_factor_auth"):
		frappe.throw(_("Two-factor sign-in is off for the workspace."))
	clear_default(user + "_otplogin")
	clear_default(user + "_otpsecret")
	tell.two_factor_reset(user)


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
		if key(f"{one['device']}|{one['address']}") == key_of and row.sid != hash_sid(frappe.session.sid):
			delete_session(user=frappe.session.user, reason="Signed out from Settings", sid_hash=row.sid)
			ended += 1
	return ended


@frappe.whitelist(allow_guest=True, methods=["POST"])
def update_password(
	new_password: str, logout_all_sessions: int = 0, key: str | None = None, old_password: str | None = None
):
	"""Frappe's own password change (the reset link and Settings alike), then
	the person is told. Named in hooks.py under override_whitelisted_methods."""
	from frappe.core.doctype.user.user import update_password as frappes

	from onedesk.one import tell
	from onedesk.account_center import invite

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
