"""Who pressed the button, proved by the phone that holds their passkey.

A passkey is a key pair the phone makes and keeps in its secure hardware or its
keychain. Registering one is a prompt; using one is Face ID, a fingerprint or
the device PIN, and every call here asks for `user_verification="required"` so
that happens on every clock-in rather than only the first.

**One credential per employee**, and a second needs HR to reset the first. That
rule is the gate. A colleague who knows your password and signs in as you on
their own phone finds no passkey there and cannot make one, so they cannot clock
in as you; the only way through is your actual phone with your face or PIN.

**The credential id is the device identity.** It is stable, it is cryptographic,
and unlike a cookie it survives clearing browser data and is not stepped around
by a private window, because it lives in the operating system's keychain rather
than in the browser profile. There is no cookie here and there was never a good
reason for one.

Verification is `py_webauthn`'s. Writing CBOR parsing and COSE key handling
ourselves would be security-critical code with no reason to be ours.
"""

import base64

import frappe
import webauthn
from frappe import _
from frappe.utils import now_datetime
from webauthn.helpers.structs import (
	AuthenticatorSelectionCriteria,
	PublicKeyCredentialDescriptor,
	ResidentKeyRequirement,
	UserVerificationRequirement,
)

from onedesk.one_hr import own, policy, rules

#: How long a challenge is good for. Long enough to find your glasses, short
#: enough that one left lying around is no use to anybody.
CHALLENGE_SECONDS = 300


@frappe.whitelist()
def start_registration() -> dict:
	"""Options for a phone to make a passkey with. Refuses a second one."""
	employee = own.employee_of()
	if not employee:
		frappe.throw(_("Only an employee can register a passkey."), frappe.PermissionError)

	if held_by(employee):
		frappe.throw(
			_("This employee already has a passkey. HR must reset it before another can be registered.")
		)

	# `held_by` asks for an Active credential, so without this a blocked
	# employee would simply register a new passkey and carry on.
	if is_blocked(employee):
		frappe.throw(
			_("This employee's passkey is blocked. HR must reset it before another can be registered.")
		)

	if policy.on("one_passkey_phone_only") and not rules.is_phone(_agent()):
		frappe.throw(
			_(
				"Register your passkey on your phone rather than on this computer. "
				"A passkey registered on a shared machine can be used by anyone sitting at it."
			)
		)

	name = frappe.db.get_value("Employee", employee, "employee_name") or employee
	options = webauthn.generate_registration_options(
		rp_id=rp_id(),
		rp_name=frappe.get_website_settings("app_name") or "One",
		user_id=employee.encode(),
		user_name=frappe.session.user,
		user_display_name=name,
		# Discoverable, so the same credential can sign them in later without
		# anybody typing an address.
		authenticator_selection=AuthenticatorSelectionCriteria(
			resident_key=ResidentKeyRequirement.PREFERRED,
			user_verification=UserVerificationRequirement.REQUIRED,
		),
	)
	_remember(options.challenge)
	return frappe.parse_json(webauthn.options_to_json(options))


@frappe.whitelist()
def finish_registration(credential: str, seen: str | dict | None = None) -> dict:
	"""Verify what the phone made, and keep it."""
	employee = own.employee_of()
	if not employee:
		frappe.throw(_("Only an employee can register a passkey."), frappe.PermissionError)
	if held_by(employee):
		frappe.throw(_("This employee already has a passkey."))

	try:
		done = webauthn.verify_registration_response(
			credential=frappe.parse_json(credential) if isinstance(credential, str) else credential,
			expected_challenge=_recall(),
			expected_rp_id=rp_id(),
			expected_origin=origin(),
			require_user_verification=True,
		)
	except Exception as error:
		frappe.throw(_("That passkey could not be verified: {0}").format(error))

	seen = frappe.parse_json(seen) if isinstance(seen, str) else (seen or {})
	device = frappe.new_doc("Clock Device")
	device.update(
		{
			"employee": employee,
			"label": rules.device_label(seen),
			"status": "Active",
			"registered_on": now_datetime(),
			"credential_id": _b64(done.credential_id),
			"public_key": _b64(done.credential_public_key),
			"sign_count": done.sign_count,
			"aaguid": done.aaguid,
			"backed_up": int(bool(done.credential_backed_up)),
			"last_address": frappe.local.request_ip,
			**{key: seen.get(key) for key in ("user_agent", "platform", "model", "screen", "renderer")},
		}
	)
	device.insert(ignore_permissions=True)
	return {"device": device.name, "label": device.label}


@frappe.whitelist()
def start_assertion(employee: str | None = None) -> dict:
	"""Options for a phone to sign a challenge with.

	Takes an employee only so the login page can ask before anybody has a
	session; from inside the desk it is always the caller's own.
	"""
	employee = employee if frappe.session.user == "Guest" else own.employee_of()
	device = held_by(employee) if employee else None

	options = webauthn.generate_authentication_options(
		rp_id=rp_id(),
		allow_credentials=(
			[PublicKeyCredentialDescriptor(id=_bytes(device.credential_id))] if device else None
		),
		user_verification=UserVerificationRequirement.REQUIRED,
	)
	_remember(options.challenge)
	return frappe.parse_json(webauthn.options_to_json(options))


def check(credential, employee: str) -> dict:
	"""Whether this assertion is that employee's passkey, unlocked by them.

	Answers rather than throws: the gates decide what a failure costs, and this
	one is asked even where the workspace has the gate set to flag.
	"""
	device = held_by(employee)
	if not device:
		return {"device": None, "verified": False, "why": "no-passkey"}

	credential = frappe.parse_json(credential) if isinstance(credential, str) else credential
	try:
		done = webauthn.verify_authentication_response(
			credential=credential,
			expected_challenge=_recall(),
			expected_rp_id=rp_id(),
			expected_origin=origin(),
			credential_public_key=_bytes(device.public_key),
			credential_current_sign_count=device.sign_count or 0,
			require_user_verification=True,
		)
	except Exception:
		return {"device": None, "verified": False, "why": "passkey-unverified"}

	if _b64(done.credential_id) != device.credential_id:
		return {"device": None, "verified": False, "why": "no-passkey"}

	frappe.db.set_value(
		"Clock Device",
		device.name,
		{
			"sign_count": done.new_sign_count,
			"last_used": now_datetime(),
			"last_address": frappe.local.request_ip,
		},
		update_modified=False,
	)
	return {"device": device.name, "verified": bool(done.user_verified), "why": ""}


def held_by(employee: str):
	"""The one Active credential this employee has, or nothing."""
	if not employee:
		return None
	found = frappe.get_all(
		"Clock Device",
		filters={"employee": employee, "status": "Active"},
		fields=["name", "credential_id", "public_key", "sign_count", "label", "user_agent"],
		order_by="creation desc",
		limit=1,
		ignore_permissions=True,
	)
	return frappe._dict(found[0]) if found else None


@frappe.whitelist()
def ask_for_a_reset(why: str | None = None) -> dict:
	"""The employee's side of a new phone: a note HR sees the same morning.

	The comparison goes in the note rather than leaving HR to guess, so
	"same model, same network, new phone" reads differently from "different
	everything" without anybody opening two records.
	"""
	employee = own.employee_of()
	if not employee:
		frappe.throw(_("Only an employee can ask for their own passkey to be reset."))

	device = held_by(employee)
	name = frappe.db.get_value("Employee", employee, "employee_name") or employee
	told = _(
		"{0} cannot check in and reports that their phone has changed.\n\n"
		"Registered on: {1}\nAsking from: {2}\nAddress: {3}\n\n{4}"
	).format(
		name,
		(device or {}).get("user_agent") or _("no passkey registered"),
		_agent(),
		frappe.local.request_ip,
		why or "",
	)

	from frappe.desk.form.assign_to import add

	for user in _hr_users():
		add(
			{
				"assign_to": [user],
				"doctype": "Employee",
				"name": employee,
				"description": told,
				"priority": "High",
			}
		)
	return {"told": len(_hr_users())}


@frappe.whitelist()
def reset(employee: str) -> dict:
	"""HR's one click, and the only way a block is lifted.

	The old credential is retired, never deleted.

	Retired rather than removed because a credential that vanishes takes the
	history of what it did with it, and the second reset inside a month is one
	of the signals worth having.
	"""
	if not frappe.has_permission("Clock Device", "write"):
		frappe.throw(_("Only HR can reset a passkey."), frappe.PermissionError)

	found = frappe.get_all(
		"Clock Device", filters={"employee": employee, "status": ["!=", "Reset"]}, pluck="name"
	)
	for name in found:
		frappe.db.set_value("Clock Device", name, "status", "Reset")
	return {"reset": len(found)}


def is_blocked(employee: str) -> bool:
	"""Whether anything this employee holds has been blocked.

	A block is lifted by a reset and by nothing else, which is why `reset`
	retires a blocked credential as well as an active one.
	"""
	return bool(frappe.db.exists("Clock Device", {"employee": employee, "status": "Blocked"}))


def block(employee: str) -> int:
	"""Retire every credential this employee holds, for good.

	Blocked rather than Reset: a reset says another phone is coming, and
	`start_registration` lets them make one. Somebody who has left is not
	making another.
	"""
	found = frappe.get_all(
		"Clock Device",
		filters={"employee": employee, "status": ["!=", "Blocked"]},
		pluck="name",
		ignore_permissions=True,
	)
	for name in found:
		frappe.db.set_value("Clock Device", name, "status", "Blocked")
	return len(found)


@frappe.whitelist()
def retire(employee: str) -> int:
	"""HR's other click: block instead of reset.

	`block` itself is the offboarding path and runs without a reader, so the
	door from a screen is here, where the permission is checked.
	"""
	if not frappe.has_permission("Clock Device", "write"):
		frappe.throw(_("Only HR can block a passkey."), frappe.PermissionError)
	return block(employee)


def resets_since(employee: str, since) -> int:
	return frappe.db.count(
		"Clock Device", {"employee": employee, "status": "Reset", "modified": [">=", since]}
	)


def rp_id() -> str:
	"""The domain the credential belongs to, without its port.

	Read from the request rather than configured, so a site reached on its own
	hostname works with no setting to get wrong. A passkey is bound to this, so
	moving a site to a new domain means everybody registers again — which is
	WebAuthn's design and not something we can or should route around.
	"""
	host = frappe.local.request.host if frappe.local.request else frappe.local.site
	return str(host).split(":")[0]


def origin() -> str:
	if frappe.local.request:
		return frappe.local.request.host_url.rstrip("/")
	return f"https://{frappe.local.site}"


def _remember(challenge: bytes) -> None:
	frappe.cache.set_value(
		_key(), base64.b64encode(challenge).decode(), expires_in_sec=CHALLENGE_SECONDS
	)


def _recall() -> bytes:
	held = frappe.cache.get_value(_key())
	if not held:
		frappe.throw(_("This request expired. Try again."))
	frappe.cache.delete_value(_key())
	return base64.b64decode(held)


def _key() -> str:
	return f"one-passkey-challenge:{frappe.session.sid or frappe.session.user}"


def _agent() -> str:
	if not frappe.local.request:
		return ""
	return frappe.local.request.headers.get("User-Agent") or ""


def _hr_users() -> list[str]:
	return frappe.get_all(
		"Has Role",
		filters={"role": ["in", ["HR User", "HR Manager"]], "parenttype": "User"},
		pluck="parent",
		distinct=True,
	)


def _b64(raw: bytes) -> str:
	return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _bytes(raw: str) -> bytes:
	return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
