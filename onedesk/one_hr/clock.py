"""Clocking yourself in and out. The one thing here that writes."""

import base64

import frappe
from frappe import _
from onedesk.one_hr import away, gates, ledger, own, policy, presence, rules, tell

IN = "IN"
OUT = "OUT"

DIRECTIONS = {"in": OUT, "late": OUT, "out": IN, "absent": IN, "unknown": IN}


@frappe.whitelist()
def ready() -> dict:
	"""What the control should show, and what this clock-in will be asked for.

	Answered before the button is drawn rather than after it is pressed, so a
	workspace that does not record positions never shows anybody a location
	prompt, and one that does says which office where somebody can read it
	instead of refusing them at the turnstile.
	"""
	employee = own.employee_of()
	if not employee or not policy.self_service():
		return {"direction": "", "why": "off" if employee else "no-employee"}

	from onedesk.one_hr import passkey

	state = presence.of(employee)
	places = gates.places_of(employee)
	start = shift_start(employee)
	return {
		"direction": DIRECTIONS.get(state.get("state"), ""),
		"state": state.get("state") or "",
		"since": state.get("since") or "",
		"due": str(start) if start else "",
		"late": is_late(employee, state, start),
		"why": "" if DIRECTIONS.get(state.get("state")) else state.get("state") or "",
		"needs": {
			"passkey": bool(policy.on("one_gate_passkey")),
			"place": bool(policy.on("one_gate_place")),
			"photo": bool(policy.on("one_gate_photo")),
		},
		"registered": bool(passkey.held_by(employee)),
		"at": _at(places),
	}


def shift_start(employee: str):
	"""When this person's shift starts today, from HRMS's own lookup: their
	assignment, else their default shift. None without one."""
	from frappe.utils import get_datetime, getdate, now_datetime
	from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift

	found = get_employee_shift(employee, now_datetime(), consider_default_shift=True)
	start = found and found.get("start_datetime")
	return get_datetime(start) if start and getdate(start) == getdate() else None


def is_late(employee: str, state: dict, start) -> bool:
	"""Past the shift's start by more than the grace: the first check-in today
	came after it, or there is none yet and the time has gone."""
	from frappe.utils import get_datetime, getdate, now_datetime, time_diff_in_seconds

	if not start:
		return False
	if state.get("state") in ("unknown", "absent"):
		return time_diff_in_seconds(now_datetime(), start) > presence.GRACE
	if state.get("state") != "in":
		return False
	first = frappe.get_all(
		"Employee Checkin",
		filters={"employee": employee, "log_type": IN, "time": [">=", f"{getdate()} 00:00:00"]},
		pluck="time",
		order_by="time asc",
		limit=1,
		ignore_permissions=True,
	)
	return bool(first) and time_diff_in_seconds(get_datetime(first[0]), start) > presence.GRACE


@frappe.whitelist(methods=["POST"])
def punch(credential=None, position=None, seen=None, reason=None, photo=None) -> dict:
	"""Clock in or out. Every gate is asked; the score decides; the row is written.

	The attempt is written whatever happens, including when a gate refused and
	including when HRMS then threw on the document. A ledger written only on the
	happy path is a ledger of the wrong half.
	"""
	employee = own.employee_of()
	if not employee:
		frappe.throw(_("Only an employee can check in."), frappe.PermissionError)
	if not policy.self_service():
		frappe.throw(_("Checking yourself in is not enabled on this site."))

	said = len(frappe.local.message_log)

	seen = frappe.parse_json(seen) if isinstance(seen, str) else (seen or {})
	position = frappe.parse_json(position) if isinstance(position, str) else (position or {})

	state = presence.of(employee)
	direction = DIRECTIONS.get(state.get("state"))
	if not direction:
		frappe.throw(_("There is nothing to check in: you are {0} today.").format(state.get("state")))

	when = ledger.stamp()
	places = gates.places_of(employee)

	who = gates.passkey_gate(employee, credential, seen)
	network = gates.network_gate(employee, places)
	place = gates.place_gate(employee, places, position)
	history = gates.history_gate(employee, seen, position, when)
	agreed = away.approved(employee, when)

	signals = _signals(who, network, place, history, agreed)
	score = rules.confidence(signals)
	outcome = rules.outcome(
		score,
		policy.band("refuse_below", rules.REFUSE_BELOW),
		policy.band("flag_below", rules.FLAG_BELOW),
	)

	attempt = ledger.write(
		employee,
		direction,
		seen,
		signals,
		device=who["device"],
		verified=who["verified"],
		address=network["address"],
		network=network["network"],
		session_address=history["session_address"],
		away=agreed or "",
		**{k: v for k, v in place.items() if k != "signals"},
	)

	if photo:
		_keep(attempt, photo)

	if outcome == "Refused":
		del frappe.local.message_log[said:]
		return _refused(attempt, score, signals)

	try:
		checkin = _write(employee, direction, place, reason, attempt)
	except frappe.ValidationError as refused:
		frappe.db.rollback()
		frappe.db.set_value("Clock Attempt", attempt, "outcome", "Refused", update_modified=False)
		frappe.db.commit()
		told = [str(refused)]
		del frappe.local.message_log[said:]
		return {"ok": False, "attempt": attempt, "score": score, "told": told}

	ledger.mark(attempt, checkin)
	if outcome == "Flagged":
		tell.check_in_flagged(attempt, employee, signals)
	del frappe.local.message_log[said:]
	return {
		"ok": True,
		"direction": direction,
		"checkin": checkin,
		"attempt": attempt,
		"score": score,
		"flagged": outcome == "Flagged",
		"told": [_(rules.says(name)) for name in signals],
	}


def _signals(who, network, place, history, agreed=None) -> list[str]:
	"""Every doubt raised, with the two rules that are about where somebody is."""
	signals = list(who["signals"]) + list(history["signals"])
	said = list(network["signals"]) + list(place["signals"])

	if agreed:
		return signals + away.forgive(said)

	if not policy.both_gates():
		network_passed = bool(network["network"])
		place_passed = place["position_state"] == "Given" and "place-outside" not in place["signals"]
		if network_passed or place_passed:
			said = [s for s in said if s not in ("network-unknown", "place-outside", "place-absent")]

	return signals + said


def _refused(attempt: str, score: int, signals: list[str]) -> dict:
	"""Refusing says what was wrong, in sentences, and never more than three.

	A refusal nobody can act on is a phone call to HR, and the three that cost
	the most confidence are the three worth reading.
	"""
	worst = sorted(set(signals), key=rules.weight, reverse=True)[:3]
	return {
		"ok": False,
		"attempt": attempt,
		"score": score,
		"told": [_(rules.says(name)) for name in worst],
	}


def _write(employee: str, direction: str, place: dict, reason, attempt: str) -> str:
	said = len(frappe.local.message_log)

	log = frappe.new_doc("Employee Checkin")
	log.flags.one_gated = True
	log.employee = employee
	log.log_type = direction
	log.one_attempt = attempt
	if place.get("latitude"):
		log.latitude = place["latitude"]
		log.longitude = place["longitude"]
	if reason and policy.on("one_reason_on_out") and direction == OUT:
		log.one_reason = reason
	log.insert()
	del frappe.local.message_log[said:]
	return log.name


def _keep(attempt: str, photo: str) -> None:
	"""The frame, as a private file on the attempt.

	Private, and swept by the retention setting in `healing.forget_photos`. A
	photograph of somebody's face is personal data everywhere and biometric data
	in several places, and the cheapest way to hold that responsibly is not to
	hold it long.
	"""
	from frappe.utils.file_manager import save_file

	head, _, body = str(photo).partition(",")
	if "image/jpeg" not in head or not body:
		return
	saved = save_file(
		f"{attempt}.jpg", base64.b64decode(body), "Clock Attempt", attempt, is_private=1
	)
	frappe.db.set_value("Clock Attempt", attempt, "photo", saved.file_url, update_modified=False)


def _at(places: list[str]) -> str:
	if not places:
		return ""
	return frappe.db.get_value("Shift Location", places[0], "location_name") or ""
