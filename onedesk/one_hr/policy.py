"""What this workspace has asked for, read from HR Settings in one place."""

import frappe

DEFAULTS = {
	"one_self_checkin": 0,
	"one_gate_passkey": 1,
	"one_gate_network": 1,
	"one_gate_place": 1,
	"one_gate_photo": 0,
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
	"one_lates_per_absence": 0,
	"one_keep_photo_days": 7,
	"standard_working_hours": 8,
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
