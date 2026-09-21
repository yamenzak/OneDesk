"""Clocking yourself in and out. The one thing here that writes.

**What makes it safe is that it takes no employee.** There is no argument to
point at a colleague: the row is written for `own.employee_of()` and for nobody
else, so the whole question of whose clock-in this is has one answer that no
caller can influence.

**Which way it points is read, not asked.** The browser does not send IN or OUT,
because a tab open since this morning would send whichever the button said when
it loaded. The direction is the opposite of where the person already is, and
somebody on leave or on a holiday is not offered one at all — a badge-in on
approved leave is a disagreement that writing it would manufacture.

**Everything about the day is HRMS's.** The row goes in as an ordinary document
so its own validation runs: shift resolution, the duplicate window, the
geolocation radius, whatever a workspace has added. No `ignore_permissions` —
the seat's `create` grant on Employee Checkin is the permission, and `own.py` is
not a way around one.
"""

import base64

import frappe
from frappe import _
from onedesk.one_hr import gates, ledger, own, policy, presence, rules

IN = "IN"
OUT = "OUT"

#: Where somebody has to be for a direction to make sense. On leave or on a
#: holiday there is no honest answer, so the control is not offered and this
#: refuses.
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
	return {
		"direction": DIRECTIONS.get(state.get("state"), ""),
		"state": state.get("state") or "",
		"since": state.get("since") or "",
		"why": "" if DIRECTIONS.get(state.get("state")) else state.get("state") or "",
		"needs": {
			"passkey": bool(policy.on("one_gate_passkey")),
			"place": bool(policy.on("one_gate_place")),
			"photo": bool(policy.on("one_gate_photo")),
		},
		"registered": bool(passkey.held_by(employee)),
		"at": _at(places),
	}


@frappe.whitelist(methods=["POST"])
def punch(credential=None, position=None, seen=None, reason=None, photo=None) -> dict:
	"""Clock in or out. Every gate is asked; the score decides; the row is written.

	The attempt is written whatever happens, including when a gate refused and
	including when HRMS then threw on the document. A ledger written only on the
	happy path is a ledger of the wrong half.
	"""
	employee = own.employee_of()
	if not employee:
		frappe.throw(_("Only an employee can clock in."), frappe.PermissionError)
	if not policy.self_service():
		frappe.throw(_("Clocking yourself in is switched off here."))

	# This endpoint answers in what it returns and never by msgprint, so nothing
	# may reach the screen except the sentences `told` carries. Anything a gate
	# or a caught permission check leaves behind would otherwise be merged into
	# the refusal dialog, which is how "Insufficient Permission for Leave
	# Policy" ended up on top of a clock-in that was refused for two entirely
	# different reasons.
	said = len(frappe.local.message_log)

	seen = frappe.parse_json(seen) if isinstance(seen, str) else (seen or {})
	position = frappe.parse_json(position) if isinstance(position, str) else (position or {})

	state = presence.of(employee)
	direction = DIRECTIONS.get(state.get("state"))
	if not direction:
		frappe.throw(_("There is no clock-in to make: you are {0} today.").format(state.get("state")))

	when = ledger.stamp()
	places = gates.places_of(employee)

	who = gates.passkey_gate(employee, credential, seen)
	network = gates.network_gate(employee, places)
	place = gates.place_gate(employee, places, position)
	history = gates.history_gate(employee, seen, position, when)

	signals = _signals(who, network, place, history)
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
		# HRMS said no after our gates said yes — its own radius, its duplicate
		# window, a workspace's own rule. The attempt stands as the record of it
		# rather than being rolled back into silence.
		frappe.db.rollback()
		frappe.db.set_value("Clock Attempt", attempt, "outcome", "Refused", update_modified=False)
		frappe.db.commit()
		told = [str(refused)]
		del frappe.local.message_log[said:]
		return {"ok": False, "attempt": attempt, "score": score, "told": told}

	ledger.mark(attempt, checkin)
	del frappe.local.message_log[said:]
	return {
		"ok": True,
		"direction": direction,
		"checkin": checkin,
		"attempt": attempt,
		"score": score,
		"flagged": outcome == "Flagged",
		"told": [rules.says(name) for name in signals],
	}


def _signals(who, network, place, history) -> list[str]:
	"""Every doubt raised, with the one rule that is about the pair of them.

	The network and the place prove the same thing two ways. Either satisfying
	it is the sensible default — demanding both means one poor GPS fix stops
	somebody working — so where the workspace has not asked for both, a gate
	that passed cancels the other's complaint.
	"""
	signals = list(who["signals"]) + list(history["signals"])
	said = list(network["signals"]) + list(place["signals"])

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
		"told": [rules.says(name) for name in worst],
	}


def _write(employee: str, direction: str, place: dict, reason, attempt: str) -> str:
	# Anything an `after_insert` hook says is by definition not about whether
	# the document was accepted, because it was. HRMS's telemetry claims a
	# milestone row on every check-in and swallows the duplicate in a savepoint
	# — but the message survives the savepoint, so every clock-in after the
	# first would put "Duplicate Name" in front of somebody who had just
	# successfully clocked in.
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
