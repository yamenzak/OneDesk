"""Who pressed the button, proved by the phone that holds their passkey."""

import base64
import hashlib

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

from onedesk.one.roles import ADMINISTRATOR
from onedesk.one_hr import own, policy, rules

#: How long a challenge is good for. Long enough to find your glasses, short
#: enough that one left lying around is no use to anybody.
CHALLENGE_SECONDS = 300


@frappe.whitelist()
def start_registration() -> dict:
	"""Options for a device to make a passkey with. Refuses a second one."""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Sign in before registering a passkey."), frappe.PermissionError)
	employee = own.employee_of()
	_may_register(user, employee)

	options = webauthn.generate_registration_options(
		rp_id=rp_id(),
		rp_name=frappe.get_website_settings("app_name") or "One",
		# A hash rather than the address, which the authenticator would keep and
		# show to anybody who lists the passkeys on it.
		user_id=hashlib.sha256(user.encode()).digest()[:32],
		user_name=user,
		user_display_name=frappe.utils.get_fullname(user),
		# Discoverable, so the same credential can sign them in later without
		# anybody typing an address.
		authenticator_selection=AuthenticatorSelectionCriteria(
			resident_key=ResidentKeyRequirement.PREFERRED,
			user_verification=UserVerificationRequirement.REQUIRED,
		),
	)
	_remember(options.challenge)
	return frappe.parse_json(webauthn.options_to_json(options))


def _may_register(user: str, employee: str) -> bool:
	"""One passkey a person; for somebody the clock checks, one HR resets.

	The one exception is the computer that is theirs at work, which HR allows
	(`allow_computer`): a second passkey, on that computer. True when this is
	that one.
	"""
	if employee and is_blocked(employee):
		# `held` asks for an Active credential, so without this a blocked
		# employee would simply register a new passkey and carry on.
		frappe.throw(
			_("This employee's passkey is blocked. HR must reset it before another can be registered.")
		)
	if computer_allowed(user):
		return True

	clocked = bool(employee) and policy.self_service()
	if held(user):
		frappe.throw(
			_("This employee already has a passkey. HR must reset it before another can be registered.")
			if clocked
			else _("You already have a passkey. Remove it before registering another.")
		)

	# Every employee's, not only while the clock is on: a passkey made on the
	# office computer while it is off would check them in once it is turned on.
	if _phone_first(employee) and not rules.is_phone(_agent()):
		frappe.throw(
			_(
				"Register your passkey on your phone rather than on this computer. "
				"A passkey registered on a shared machine can be used by anyone sitting at it."
			)
		)
	return False


#: How long HR's allowance for a computer stays open.
COMPUTER_HOURS = 24


@frappe.whitelist(methods=["POST"])
def allow_computer(employee: str) -> dict:
	"""HR's click for the computer that is somebody's own at work: for the next
	day they may register a second passkey on a computer, once. Written on the
	employee's timeline, since it is a door HR opened."""
	from frappe.utils import add_to_date, format_datetime

	if not frappe.has_permission("Clock Device", "write"):
		frappe.throw(_("Only HR can allow a passkey on a computer."), frappe.PermissionError)
	user = frappe.db.get_value("Employee", employee, "user_id")
	if not user:
		frappe.throw(_("This employee has no user to sign in with."))
	until = add_to_date(now_datetime(), hours=COMPUTER_HOURS)
	frappe.defaults.set_user_default("one_passkey_computer", str(until), user)
	frappe.get_doc("Employee", employee).add_comment(
		"Info", _("May register a passkey on their office computer until {0}.").format(format_datetime(until))
	)
	return {"until": str(until)}


def computer_allowed(user: str) -> bool:
	"""Whether HR's allowance is open for this person, and this is a computer
	they have not already made one on."""
	from frappe.utils import get_datetime

	until = frappe.defaults.get_user_default("one_passkey_computer", user)
	if not until or get_datetime(until) < now_datetime() or rules.is_phone(_agent()):
		return False
	return not frappe.db.exists("Clock Device", {"user": user, "status": "Active", "computer": 1})


@frappe.whitelist()
def finish_registration(credential: str, seen: str | dict | None = None) -> dict:
	"""Verify what the device made, and keep it."""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Sign in before registering a passkey."), frappe.PermissionError)
	employee = own.employee_of()
	computer = _may_register(user, employee)

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
			"user": user,
			"employee": employee or None,
			"computer": int(computer),
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
	if computer:
		frappe.defaults.clear_user_default("one_passkey_computer", user)
	from onedesk.one import tell

	tell.passkey_added(frappe.session.user)
	return {"device": device.name, "label": device.label}


@frappe.whitelist()
def start_assertion(employee: str | None = None) -> dict:
	"""Options for a phone to sign a challenge with.

	Takes an employee only so the login page can ask before anybody has a
	session; from inside the desk it is always the caller's own.
	"""
	employee = employee if frappe.session.user == "Guest" else own.employee_of()
	keys = every(_whose(employee)) if employee else []

	options = webauthn.generate_authentication_options(
		rp_id=rp_id(),
		allow_credentials=[PublicKeyCredentialDescriptor(id=_bytes(one.credential_id)) for one in keys] or None,
		user_verification=UserVerificationRequirement.REQUIRED,
	)
	_remember(options.challenge)
	return frappe.parse_json(webauthn.options_to_json(options))


def check(credential, employee: str) -> dict:
	"""Whether this assertion is that employee's passkey, unlocked by them.

	Answers rather than throws: the gates decide what a failure costs, and this
	one is asked even where the workspace has the gate set to flag.
	"""
	credential = frappe.parse_json(credential) if isinstance(credential, str) else credential
	said = (credential or {}).get("id") or (credential or {}).get("rawId")
	device = next((one for one in every(_whose(employee)) if one.credential_id == said), None) if employee else None
	if not device:
		return {"device": None, "verified": False, "why": "no-passkey"}

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
	return _active(_whose(employee))


def held(user: str):
	"""The one Active credential this person has, or nothing."""
	if not user or user == "Guest":
		return None
	return _active({"user": user})


def _active(whose: dict):
	"""The phone's passkey before the office computer's, which HR adds."""
	found = every(whose)
	return next((one for one in found if not one.computer), found[0] if found else None)


def every(whose: dict) -> list:
	"""Every Active credential. A row with no key in it is not a passkey: it
	cannot sign, and taking it for one sends the phone a challenge for a
	credential that does not exist."""
	return [
		frappe._dict(one)
		for one in frappe.get_all(
			"Clock Device",
			filters={**whose, "status": "Active", "credential_id": ["is", "set"]},
			fields=[
				"name",
				"user",
				"credential_id",
				"public_key",
				"sign_count",
				"label",
				"user_agent",
				"backed_up",
				"computer",
			],
			order_by="creation desc",
			ignore_permissions=True,
		)
	]


def _whose(employee: str) -> dict:
	"""An employee's passkeys are their login's: one registered before they
	were an employee is theirs too."""
	user = frappe.db.get_value("Employee", employee, "user_id")
	return {"user": user} if user else {"employee": employee}


@frappe.whitelist(methods=["POST"])
def remove() -> dict:
	"""The person's own passkey, retired so they can register another.

	Not for somebody the clock checks: their new phone is HR's to allow, which
	is the point of a reset, so they ask for one instead.
	"""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Sign in first."), frappe.PermissionError)
	if own.employee_of() and policy.self_service():
		frappe.throw(_("Your passkey also checks you in, so HR resets it. Ask HR for a reset."))
	found = frappe.get_all(
		"Clock Device", filters={"user": user, "status": "Active"}, pluck="name", ignore_permissions=True
	)
	for name in found:
		frappe.db.set_value("Clock Device", name, "status", "Reset")
	return {"removed": len(found)}


#: How often somebody without a passkey is offered one after signing in, and
#: how many "Not now"s it takes to stop asking. Settings still offers it.
ASK_EVERY_DAYS = 7
ASK_TIMES = 3


def ask() -> bool:
	"""Whether to offer this person a passkey now: sign-in by passkey is on,
	they have none, they have not said "Not now" too often or too lately, and
	this device is one they could make it on."""
	from frappe.utils import date_diff, today

	from onedesk.one_hr import signin

	user = frappe.session.user
	if user in ("Guest", "Administrator") or not signin.offered():
		return False
	if computer_allowed(user):
		return True
	if held(user):
		return False
	employee = own.employee_of()
	if employee and is_blocked(employee):
		return False
	times, last = _asked(user)
	if times >= ASK_TIMES or (last and date_diff(today(), last) < ASK_EVERY_DAYS):
		return False
	return not (_phone_first(employee) and not rules.is_phone(_agent()))


def _phone_first(employee: str) -> bool:
	"""Whether this person's passkey has to be made on a phone: an employee's,
	where HR asks for that."""
	return bool(employee) and bool(policy.on("one_passkey_phone_only"))


@frappe.whitelist(methods=["POST"])
def not_now() -> None:
	"""The offer was turned down: asked again in a week, and not after three."""
	from frappe.utils import today

	times, _last = _asked(frappe.session.user)
	frappe.defaults.set_user_default("one_passkey_asked", f"{times + 1},{today()}")


def _asked(user: str) -> tuple[int, str]:
	said = frappe.defaults.get_user_default("one_passkey_asked", user) or ""
	times, _, last = said.partition(",")
	return (int(times) if times.isdigit() else 0), last


def query(user: str | None = None) -> str:
	"""HR reads employees' passkeys, everybody their own, and the workspace's
	administrator all of them. An administrator's passkey is not HR's business."""
	user = user or frappe.session.user
	roles = frappe.get_roles(user)
	if ADMINISTRATOR in roles or user == "Administrator":
		return ""
	mine = f"`tabClock Device`.user = {frappe.db.escape(user)}"
	if {"HR User", "HR Manager"} & set(roles):
		return f"(ifnull(`tabClock Device`.employee, '') != '' or {mine})"
	return mine


def has_permission(doc, ptype=None, user=None) -> bool | None:
	user = user or frappe.session.user
	roles = frappe.get_roles(user)
	if ADMINISTRATOR in roles or user == "Administrator" or doc.user == user:
		return None
	if {"HR User", "HR Manager"} & set(roles) and doc.employee:
		return None
	return False


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
	from onedesk.one_hr import tell

	tell.passkey_reset_asked(
		employee,
		registered=(device or {}).get("user_agent") or _("no passkey registered"),
		asking=_agent(),
		address=frappe.local.request_ip,
		why=why or "",
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
		"Clock Device",
		filters={**_whose(employee), "status": ["!=", "Reset"]},
		pluck="name",
		ignore_permissions=True,
	)
	for name in found:
		frappe.db.set_value("Clock Device", name, "status", "Reset")
	if found:
		from onedesk.one_hr import tell

		tell.passkey_reset_done(employee)
	return {"reset": len(found)}


def is_blocked(employee: str) -> bool:
	"""Whether anything this employee holds has been blocked.

	A block is lifted by a reset and by nothing else, which is why `reset`
	retires a blocked credential as well as an active one.
	"""
	return bool(frappe.db.exists("Clock Device", {**_whose(employee), "status": "Blocked"}))


def block(employee: str) -> int:
	"""Retire every credential this employee holds, for good.

	Blocked rather than Reset: a reset says another phone is coming, and
	`start_registration` lets them make one. Somebody who has left is not
	making another.
	"""
	found = frappe.get_all(
		"Clock Device",
		filters={**_whose(employee), "status": ["!=", "Blocked"]},
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
		"Clock Device", {**_whose(employee), "status": "Reset", "modified": [">=", since]}
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


#: Before anybody signs in, frappe gives every browser the same sid ("Guest"),
#: so a challenge keyed by it is one slot shared by everybody on the login page.
BINDER = "one_passkey"


def _remember(challenge: bytes) -> None:
	if frappe.session.user == "Guest" and frappe.local.request:
		binder = frappe.generate_hash()
		frappe.local.cookie_manager.set_cookie(BINDER, binder, max_age=CHALLENGE_SECONDS, httponly=True)
		key = _key(binder)
	else:
		key = _key()
	frappe.cache.set_value(key, base64.b64encode(challenge).decode(), expires_in_sec=CHALLENGE_SECONDS)


def _recall() -> bytes:
	key = _key(frappe.request.cookies.get(BINDER) if frappe.session.user == "Guest" and frappe.local.request else None)
	held = frappe.cache.get_value(key)
	if not held:
		frappe.throw(_("This request expired. Try again."))
	frappe.cache.delete_value(key)
	return base64.b64decode(held)


def _key(binder: str | None = None) -> str:
	if frappe.session.user == "Guest":
		return f"one-passkey-challenge:guest:{binder or 'none'}"
	return f"one-passkey-challenge:{frappe.session.sid}"


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
