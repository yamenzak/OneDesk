"""Every clock-in tried, written down whether it was allowed or refused.

`Employee Checkin` only records successes, and the refusals are the interesting
ones. So each attempt writes a `Checkin Attempt` of its own carrying what every
gate saw, and that table is three things at once: the review queue, the evidence
when somebody disputes a day, and what the self-healing reads.

The row is written last and always, including when a gate refused and including
when writing the check-in itself threw. A ledger that is only written on the
happy path is a ledger of the wrong half.
"""

import frappe
from frappe.utils import now_datetime

from onedesk.one_hr import rules

#: What the browser tells us about itself, and what we call each one. None of it
#: is identity — the passkey is that. It is what makes a reset request
#: recognisable and what shows several people enrolling from one machine.
SEEN = ("user_agent", "platform", "model", "screen", "renderer")


def write(employee: str, direction: str, seen: dict, signals: list[str], **found) -> str:
	"""One attempt, with its signals and its score. Returns the row's name."""
	score = rules.confidence(signals)
	attempt = frappe.new_doc("Checkin Attempt")
	attempt.update(
		{
			"employee": employee,
			"direction": direction or "",
			"outcome": rules.outcome(score, *_bands()),
			"score": score,
			**{key: (seen or {}).get(key) for key in SEEN},
			**found,
		}
	)
	for name in dict.fromkeys(signals):
		attempt.append(
			"signals", {"signal": name, "weight": rules.weight(name), "says": rules.says(name)}
		)
	attempt.insert(ignore_permissions=True)
	return attempt.name


def mark(name: str, checkin: str) -> None:
	"""Point the attempt at the log it produced, once HRMS has accepted it."""
	frappe.db.set_value("Checkin Attempt", name, "checkin", checkin, update_modified=False)


def recent(employee: str, since) -> list[dict]:
	"""This employee's attempts since a moment, oldest first.

	Read with `ignore_permissions` on purpose: this is the gates reading their
	own history to judge the attempt in front of them, not a person reading
	somebody else's record. Nothing from here reaches a screen.
	"""
	return frappe.get_all(
		"Checkin Attempt",
		filters={"employee": employee, "creation": [">=", since]},
		fields=["name", "creation", "outcome", "score", "address", "latitude", "longitude"],
		order_by="creation asc",
		ignore_permissions=True,
	)


def others_on(seen: dict, employee: str, since) -> list[str]:
	"""Other people who clocked in from what looks like this same browser.

	Not a device check — the passkey is that, and this cannot see one. It is the
	shared reception machine showing itself: same user agent, same screen, same
	graphics chip, several employees, one morning.
	"""
	fingerprint = {key: (seen or {}).get(key) for key in ("user_agent", "screen", "renderer")}
	if not all(fingerprint.values()):
		return []

	found = frappe.get_all(
		"Checkin Attempt",
		filters={**fingerprint, "employee": ["!=", employee], "creation": [">=", since]},
		pluck="employee",
		ignore_permissions=True,
	)
	return sorted(set(found))


def same_second(when, employee: str) -> bool:
	"""Whether somebody else's attempt landed in the same second, which is a script."""
	return bool(
		frappe.get_all(
			"Checkin Attempt",
			filters={
				"employee": ["!=", employee],
				"creation": ["between", [when.replace(microsecond=0), when]],
			},
			limit=1,
			ignore_permissions=True,
		)
	)


def stamp() -> object:
	"""The server's clock, which is the only one worth reading."""
	return now_datetime()


def _bands() -> tuple[int, int]:
	from onedesk.one_hr import policy

	return policy.band("refuse_below", rules.REFUSE_BELOW), policy.band(
		"flag_below", rules.FLAG_BELOW
	)
