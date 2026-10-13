"""Point 6: nothing frappe, erpnext or hrms gives is lost. Every record type,
report and page they ship, and ours, is reached in One (a rail, a Home, our
screens, a form's link or Connections, a list's Related Reports), or answered
in onedesk/one/atlas.py, or counted here as still to decide. The count only
falls, and an update that brings something new fails until it is placed.
scripts/atlas.py draws the map; docs/ATLAS.md is the result."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import atlas

#: What each module still has with no way in and no answer. Lower it as each
#: is placed or answered; it may never rise.
WAITING = {
	"erpnext / Accounts": 57,
	"erpnext / Assets": 4,
	"erpnext / Bulk Transaction": 2,
	"erpnext / Buying": 1,
	"erpnext / CRM": 3,
	"erpnext / Communication": 1,
	"erpnext / EDI": 2,
	"erpnext / ERPNext Integrations": 1,
	"erpnext / Maintenance": 2,
	"erpnext / Manufacturing": 9,
	"erpnext / Projects": 2,
	"erpnext / Quality Management": 9,
	"erpnext / Regional": 4,
	"erpnext / Selling": 5,
	"erpnext / Setup": 7,
	"erpnext / Stock": 30,
	"erpnext / Support": 1,
	"erpnext / Telephony": 4,
	"erpnext / Utilities": 4,
	"frappe / Automation": 7,
	"frappe / Contacts": 1,
	"frappe / Core": 55,
	"frappe / Custom": 4,
	"frappe / Desk": 27,
	"frappe / Email": 7,
	"frappe / Integrations": 13,
	"frappe / Printing": 7,
	"frappe / Website": 18,
	"frappe / Workflow": 2,
	"hrms / HR": 12,
	"hrms / Payroll": 7,
}

#: What an answer may say a thing is (onedesk/one/atlas.py).
KINDS = {"engine", "inside", "replaced", "left out"}


def test_nothing_waits_that_was_not_waiting():
	now = {module: len(names) for module, names in atlas.waiting().items()}
	grown = {module: (n, WAITING.get(module, 0)) for module, n in now.items() if n > WAITING.get(module, 0)}
	assert not grown, (
		f"placed nowhere and not answered (now, allowed): {grown}. Place it or answer it in onedesk/one/atlas.py: { {m: atlas.waiting()[m] for m in grown} }"
	)


def test_the_counts_are_lowered_as_things_are_placed():
	now = {module: len(names) for module, names in atlas.waiting().items()}
	stale = {module: (now.get(module, 0), n) for module, n in WAITING.items() if now.get(module, 0) < n}
	assert not stale, f"lower WAITING to what is still waiting (now, written): {stale}"


def test_every_answer_names_something_unreached():
	"""An answer for something the map now reaches, or that no longer exists,
	is a stale line."""
	reached = {(row["kind"], row["name"]) for row in atlas.rows() if row["reach"]}
	known = {(row["kind"], row["name"]) for row in atlas.rows()}
	said = atlas.answers()
	assert not set(said) - known, sorted(set(said) - known)
	assert not set(said) & reached, f"reached now, take the answer out: {sorted(set(said) & reached)}"
	assert {kind for kind, _ in said.values()} <= KINDS


def test_the_map_finds_a_way_in():
	"""The reader of rails, links and Connections still works."""
	reach = atlas.reach()
	assert reach[("DocType", "Item")][0] == "named"
	assert reach[("DocType", "Warehouse Type")][0] == "linked"
	assert ("DocType", "Putaway Rule") not in reach, "a read-only link is no way in"


def test_the_atlas_is_current():
	assert (atlas.tree.ROOT / "docs" / "ATLAS.md").read_text() == atlas.page(), "run python scripts/docs.py"
