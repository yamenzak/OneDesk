"""Signing in with the same passkey somebody clocks in with.

An employee who only ever clocks in has no reason to hold a password, and a
password they never type is a password they write down. The credential is
already discoverable — `start_registration` asks for a resident key — so the
browser offers the account and nothing is typed at all.

**This is the only place in One that logs somebody in**, and it does it through
`frappe.local.login_manager`, which is the same path the password form takes:
the session, the login hooks, the rate limiter and the audit trail are all
frappe's. Verifying a signature and then setting a session by hand would be a
second way into the product, and a second way in is the one thing a login page
must not have.
"""

import frappe
import webauthn
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import now_datetime
from webauthn.helpers.structs import UserVerificationRequirement

from onedesk.one_hr import passkey


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=10, seconds=60)
def begin() -> dict:
	"""A challenge for whatever passkey the browser can find.

	No credentials are named, because naming them would mean taking an address
	from a stranger and answering whether we have one — which turns a login page
	into a way of asking who works here.
	"""
	_allowed()
	options = webauthn.generate_authentication_options(
		rp_id=passkey.rp_id(), user_verification=UserVerificationRequirement.REQUIRED
	)
	passkey._remember(options.challenge)
	return frappe.parse_json(webauthn.options_to_json(options))


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=10, seconds=60)
def finish(credential: str) -> dict:
	"""Verify the signature, find whose it is, and let frappe do the rest."""
	_allowed()
	credential = frappe.parse_json(credential) if isinstance(credential, str) else credential

	device = _device_for(credential.get("id") or credential.get("rawId"))
	if not device:
		frappe.throw(_("That passkey is not registered here."), frappe.AuthenticationError)

	try:
		done = webauthn.verify_authentication_response(
			credential=credential,
			expected_challenge=passkey._recall(),
			expected_rp_id=passkey.rp_id(),
			expected_origin=passkey.origin(),
			credential_public_key=passkey._bytes(device.public_key),
			credential_current_sign_count=device.sign_count or 0,
			require_user_verification=True,
		)
	except Exception:
		frappe.throw(_("That passkey could not be verified."), frappe.AuthenticationError)

	user = frappe.db.get_value("Employee", device.employee, "user_id")
	if not user or not frappe.db.get_value("User", user, "enabled"):
		frappe.throw(_("That passkey belongs to somebody with no account here."), frappe.AuthenticationError)

	frappe.db.set_value(
		"Clock Device",
		device.name,
		{"sign_count": done.new_sign_count, "last_used": now_datetime()},
		update_modified=False,
	)

	# `login_as` calls `post_login` itself, which runs the on_login hooks, the
	# IP and hour checks and the session. There is nothing here that a password
	# login does not also do.
	frappe.local.login_manager.login_as(user)
	return {"user": user, "home": frappe.db.get_value("User", user, "default_workspace") or "/desk"}


def _device_for(credential_id: str):
	if not credential_id:
		return None
	found = frappe.get_all(
		"Clock Device",
		filters={"credential_id": credential_id, "status": "Active"},
		fields=["name", "employee", "public_key", "sign_count"],
		limit=1,
		ignore_permissions=True,
	)
	return frappe._dict(found[0]) if found else None


#: The switch lives on System Settings rather than on HR Settings, beside
#: `disable_user_pass_login` and `login_with_email_link` in the section frappe
#: already calls Login Methods. A login method is not an HR setting.
SWITCH = "one_login_with_passkey"


def _allowed() -> None:
	if not offered():
		frappe.throw(_("Signing in with a passkey is switched off here."))


@frappe.whitelist(allow_guest=True)
def offered() -> bool:
	"""Whether the login page should draw the button at all."""
	if not frappe.get_meta("System Settings").has_field(SWITCH):
		return False
	return bool(frappe.db.get_single_value("System Settings", SWITCH))
