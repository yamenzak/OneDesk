"""What this workspace has asked for, read from HR Settings in one place.

Every switch below is a Custom Field this app adds to HRMS's own single
doctype, which is where a tenant already goes to configure HR. The reason they
are all read through here rather than with `get_single_value` scattered about:
a default typed twice is a default that will disagree with itself, and a gate
that cannot be found from one file is a gate nobody can audit.

A Single stores nothing until somebody saves it, and `get_single_value` casts a
missing Int or Check to zero rather than to None. So a default of 1 would read
as off on a site nobody has opened HR Settings on, which is how every gate would
have been silently disabled on a fresh install. `seed()` writes each default
once, at install and after every migrate, and only where the field has never
been written — so it can never overrule what a tenant chose.
"""

import frappe

#: Every switch, and what a site that has never touched it gets. Self clock-in
#: is off: a workspace turns attendance on deliberately, and one that has not
#: should not discover it because somebody found the button.
DEFAULTS = {
	"one_self_checkin": 0,
	"one_gate_passkey": 1,
	"one_gate_network": 1,
	"one_gate_place": 1,
	"one_gate_photo": 0,
	# Either the network or the place, rather than both: they prove the same
	# thing two ways, and demanding both means one flaky fix stops somebody
	# working. A workspace that means it can ask for both.
	"one_gates_require": "Either",
	"one_passkey_refuses": 1,
	"one_passkey_phone_only": 1,
	"one_learn_networks": 1,
	"one_learn_zones": 1,
	"one_learn_home": 0,
	"one_learn_threshold": 3,
	"one_refuse_below": 50,
	"one_flag_below": 85,
	"one_close_the_day": 1,
	"one_reason_on_out": 1,
	"one_keep_photo_days": 7,
	# hrms's own field rather than one of ours, and the only reading of "how
	# long is a day" the product has. Left at zero it makes every hour of a
	# shiftless day overtime, so it starts at eight.
	"standard_working_hours": 8,
	# OneAI on hiring and grievances: every automatic call starts on, and a
	# workspace that may not use one says so here. See one_hr/README.md.
	"one_ai_screen": 1,
	"one_ai_prepare": 1,
	"one_ai_record": 1,
	"one_ai_transcribe": 1,
	"one_keep_recordings_days": 365,
	"one_ai_grievances": 1,
}


def on(switch: str) -> bool:
	return bool(get(switch))


def band(which: str, fallback: int) -> int:
	value = get(f"one_{which}")
	return int(value) if value not in (None, "") else fallback


def get(switch: str):
	# Asked of the meta rather than the table: HR Settings is a Single and has
	# no table to have a column in.
	if not frappe.get_meta("HR Settings").has_field(switch):
		return DEFAULTS.get(switch)
	if not _written(switch):
		return DEFAULTS.get(switch)
	value = frappe.db.get_single_value("HR Settings", switch)
	return DEFAULTS.get(switch) if value in (None, "") else value


def seed() -> None:
	"""Write every default that has never been written. Idempotent, and run on
	every migrate, so a switch added later starts at its default rather than at
	whatever zero happens to mean for its fieldtype."""
	meta = frappe.get_meta("HR Settings")
	for switch, default in DEFAULTS.items():
		if meta.has_field(switch) and not _written(switch):
			frappe.db.set_single_value("HR Settings", switch, default)


def _written(switch: str) -> bool:
	"""Whether this field has a row of its own in `tabSingles`.

	Read with SQL because Singles is a table rather than a doctype, and the
	distinction matters: `get_single_value` cannot tell "never set" from "set to
	zero", and for a switch whose default is on those are opposites.
	"""
	return bool(
		frappe.db.sql(
			"select 1 from tabSingles where doctype = %s and field = %s limit 1",
			("HR Settings", switch),
		)
	)


def both_gates() -> bool:
	"""Whether the network and the place both have to pass, or either will do."""
	return get("one_gates_require") == "Both"


def self_service() -> bool:
	"""Whether anybody may clock themselves in here at all."""
	return on("one_self_checkin")
