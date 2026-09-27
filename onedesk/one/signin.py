"""How a person signs in, and where they are signed in: the Sign-in page of Settings.

Nothing here is a copy. Frappe already keeps all of it:

- each session in `tabSessions`, with the browser's user agent and the
  network address it was opened from, and when it was last used;
- each sign-in, and each failed one, in the Activity Log;
- when the password was last changed, on the User (`last_password_reset_date`);
- whether two-factor sign-in applies to the person (`frappe.twofactor`).

What is ours is reading it the way a person asks: "Chrome on Mac, two hours
ago", this one marked, each with Sign Out. And telling them, always by mail,
when their password changes or a passkey is added, because that is how
somebody learns their account was taken.
"""

import hashlib
import json

import frappe
from frappe import _
from frappe.utils import now_datetime

#: The sign-ins shown, newest first.
RECENT = 6

#: Browsers and systems, in the order a user agent is read: Edge and Opera say
#: "Chrome" too, and every browser on an iPhone says "Safari".
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
	"""Where the person is signed in and has not yet been signed out by time:
	the device, the address, when it was last used, and which is this one."""
	from frappe.sessions import get_expired_threshold

	user = user or frappe.session.user
	rows = frappe.db.sql(
		"""select sid, sessiondata, lastupdate from `tabSessions`
		where user = %s and status = 'Active' and lastupdate > %s order by lastupdate desc""",
		(user, get_expired_threshold()),
		as_dict=True,
	)
	here = frappe.session.sid
	out = []
	for row in rows:
		try:
			data = json.loads(row.sessiondata or "{}")
		except ValueError:
			data = {}
		out.append(
			{
				"key": key(row.sid),
				"device": device(data.get("user_agent")),
				"address": data.get("session_ip") or "",
				"last_used": row.lastupdate,
				"here": row.sid == here,
			}
		)
	# This one first, then the rest as they were last used.
	return sorted(out, key=lambda one: not one["here"])


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

	from onedesk.one_hr import own
	from onedesk.one_hr import passkey as keys
	from onedesk.one_hr import signin as passkey_signin

	user = user or frappe.session.user
	employee = own.employee_of()
	return {
		"password_changed": frappe.db.get_value("User", user, "last_password_reset_date"),
		"employee": employee,
		"passkey": bool(keys.held_by(employee)) if employee else None,
		"passkey_signs_in": bool(employee) and passkey_signin.offered(),
		"two_factor": bool(two_factor_is_enabled(user)),
		"two_factor_method": frappe.get_system_settings("two_factor_method")
		if two_factor_is_enabled(user)
		else None,
		"sessions": sessions(user),
		"recent": recent(user),
	}


@frappe.whitelist(methods=["POST"])
def sign_out(key_of: str) -> int:
	"""One of the reader's own sessions ends, found by the key the page has."""
	from frappe.sessions import delete_session

	mine = frappe.db.sql("select sid from `tabSessions` where user = %s", frappe.session.user, pluck=True)
	for row in mine:
		if key(row) == key_of and row != frappe.session.sid:
			delete_session(row, frappe.session.user, reason="Signed out from Settings")
			return 1
	return 0


# ------------------------------------------------------------------ telling


@frappe.whitelist(allow_guest=True, methods=["POST"])
def update_password(
	new_password: str, logout_all_sessions: int = 0, key: str | None = None, old_password: str | None = None
):
	"""Frappe's own password change (the reset link and Settings alike), then
	the person is told. Named in hooks.py under override_whitelisted_methods."""
	from frappe.core.doctype.user.user import update_password as frappes

	from onedesk.one import invite

	said = frappes(new_password, logout_all_sessions=logout_all_sessions, key=key, old_password=old_password)
	if frappe.local.response.get("http_status_code") != 410 and frappe.session.user != "Guest":
		# A first password, set from an invitation, is joining, not a change.
		if not invite.spend(frappe.session.user):
			told_password(frappe.session.user)
	return said


def _said() -> dict:
	"""When, from which device and address: what a security notice says."""
	agent = frappe.request.headers.get("User-Agent") if getattr(frappe.local, "request", None) else None
	return {
		"device": device(agent),
		"when": frappe.utils.format_datetime(now_datetime(), "d MMM yyyy, HH:mm"),
		"address": getattr(frappe.local, "request_ip", None) or "",
	}


def _mailed(user: str) -> tuple[str | None, str | None]:
	return frappe.db.get_value("User", user, ["email", "language"]) or (None, None)


# A security notice goes on the bell and is always mailed, so a person who did
# not do it finds out wherever they are. It is sent by the workspace rather
# than the person, or frappe would not tell them of their own act.


def told_password(user: str) -> None:
	from onedesk.one import notify

	slots, (email, lang) = _said(), _mailed(user)
	notify.notify(
		"Password Changed", user, link="/desk/settings?section=signin", sender="Administrator", **slots
	)
	if email:
		notify.mail("Password Changed", email, lang=lang, **slots)


def told_passkey(user: str) -> None:
	from onedesk.one import notify

	slots, (email, lang) = _said(), _mailed(user)
	notify.notify(
		"Passkey Added", user, link="/desk/settings?section=signin", sender="Administrator", **slots
	)
	if email:
		notify.mail("Passkey Added", email, lang=lang, **slots)
