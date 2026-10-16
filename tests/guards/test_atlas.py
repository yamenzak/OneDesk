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
	"erpnext / Accounts": 54,
	"erpnext / Bulk Transaction": 2,
	"erpnext / Communication": 1,
	"erpnext / EDI": 2,
	"erpnext / ERPNext Integrations": 1,
	"erpnext / Maintenance": 2,
	"erpnext / Projects": 2,
	"erpnext / Quality Management": 9,
	"erpnext / Regional": 4,
	"erpnext / Selling": 4,
	"erpnext / Setup": 7,
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
	"hrms / HR": 0,
	"hrms / Payroll": 0,
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
	assert reach[("DocType", "Putaway Rule")][0] == "named"
	assert ("DocType", "Stock Reposting Settings") not in reach


def test_the_atlas_is_current():
	assert (atlas.tree.ROOT / "docs" / "ATLAS.md").read_text() == atlas.page(), "run python scripts/docs.py"


# ------------------------------------------------------------------ who may open it

#: Modules whose records live on the operator's own site, where the operator
#: holds every right (one_admin).
OPERATOR = ("One Admin",)

#: What each module has that a person reaches but no role a workspace gives may
#: open. Lower it as each is opened to its people or its way in is closed.
NOBODY = {
	"erpnext / Accounts": 2,
	"erpnext / Maintenance": 1,
	"erpnext / Selling": 1,
	"erpnext / Setup": 2,
	"erpnext / Support": 4,
	"frappe / Core": 9,
	"frappe / Custom": 1,
	"frappe / Desk": 1,
	"frappe / Email": 1,
	"frappe / Integrations": 1,
	"frappe / Website": 4,
	"frappe / Workflow": 1,
	"hrms / HR": 1,
	"onedesk / One": 2,
	"onedesk / One AI": 1,
	"onedesk / One Mail": 1,
}


def _nobody() -> dict:
	out = {}
	for row in atlas.rows():
		if row["kind"] == "DocType" and row["reach"] and row["module"] not in OPERATOR:
			if atlas.open_to("DocType", row["name"]) == []:
				out.setdefault(f"{row['app']} / {row['module']}", []).append(row["name"])
	return out


def test_what_is_reached_is_open_to_somebody():
	now = _nobody()
	grown = {m: names for m, names in now.items() if len(names) > NOBODY.get(m, 0)}
	assert not grown, f"reached, but no role a workspace gives may open it: {grown}"
	stale = {m: (len(now.get(m, [])), n) for m, n in NOBODY.items() if len(now.get(m, [])) < n}
	assert not stale, f"lower NOBODY (now, written): {stale}"


def test_who_may_open_what_was_read():
	"""docs/atlas-site.json was read from the site; a demo check holds it to
	the site's (one_atlas_knows_who_may_open_what)."""
	assert atlas.readers()["doctypes"].get("Item"), "run python scripts/atlas.py --site"


# ------------------------------------------------------------------ the brand


def test_the_brand_translations_are_current():
	for lang, text in atlas.translation_files().items():
		path = atlas.TRANSLATIONS / f"{lang}.csv"
		assert path.exists() and path.read_text() == text, f"run python scripts/atlas.py --brand ({lang})"


def _unbranded(text: str) -> str:
	for name in atlas._module_dict("OUTSIDE"):
		text = text.replace(name, "")
	return text


def test_nothing_upstream_says_names_them():
	"""Every sentence frappe, erpnext or hrms say naming themselves reads One,
	in English, Arabic and German, but for an outside name kept on purpose."""
	said = atlas.rebranded()
	swapped = {msgid for msgid, _, _ in said["en"]}
	for msgid in atlas.upstream()["brand"]:
		assert msgid in swapped or not atlas.SAID_BRAND.search(_unbranded(msgid)), msgid
	for lang, rows in said.items():
		for msgid, text, _ in rows:
			assert not atlas.SAID_BRAND.search(_unbranded(text)), (lang, msgid, text)


# ------------------------------------------------------------------ our screens

#: Record types each screen lists but does not hear change. Lower it as each
#: is followed (the kit's followList); it may never rise.
UNHEARD = {
	"project": 9,
	"task": 2,
	"item": 11,
	"home": 8,
	"my_tasks": 2,
	"timers": 4,
}

#: Numbers a screen prints with no formatter around them.
BARE = {}

#: Record types a screen lists without the reader's company, in a type with one.
NOT_THE_COMPANYS = {
	"project": 8,
	"task": 2,
	"item": 9,
	"home": 5,
	"my_tasks": 2,
	"timers": 3,
}


def _held(key: str, allowed: dict) -> None:
	now = {one["screen"]: one[key] for one in atlas.screens() if one[key]}
	grown = {s: names for s, names in now.items() if len(names) > allowed.get(s, 0)}
	assert not grown, f"{key} grew: {grown}"
	stale = {s: (len(now.get(s, [])), n) for s, n in allowed.items() if len(now.get(s, [])) < n}
	assert not stale, f"lower the count (now, written): {stale}"


def test_a_screen_hears_what_it_lists():
	_held("unheard", UNHEARD)


def test_a_screen_prints_numbers_through_frappe():
	_held("bare", BARE)


def test_a_screen_lists_the_readers_company():
	_held("no_company", NOT_THE_COMPANYS)


def test_the_screens_are_read():
	"""The reader of screens still finds what Stock on Hand lists and hears."""
	stock = next(one for one in atlas.screens() if one["screen"] == "stock")
	assert "Bin" in stock["reads"] and "Bin" not in stock["unheard"]


# ------------------------------------------------------------------ the Passover points, per record type

#: Point 1. Record types a person reaches that the demo has none of.
EMPTY = {
	"erpnext / Accounts": 21,
	# Shift allocations want an asset depreciated by shift.
	"erpnext / Assets": 2,
	"erpnext / CRM": 1,
	"erpnext / Maintenance": 1,
	"erpnext / Manufacturing": 4,
	"erpnext / Projects": 1,
	"erpnext / Selling": 4,
	"erpnext / Setup": 4,
	# Placed with none on purpose: a stock dimension adds a field to every stock
	# form, and a closing refuses the history the demo writes behind it.
	"erpnext / Stock": 6,
	"erpnext / Subcontracting": 1,
	"erpnext / Support": 4,
	"frappe / Automation": 1,
	"frappe / Core": 6,
	"frappe / Desk": 1,
	"frappe / Email": 2,
	"frappe / Integrations": 5,
	"frappe / Website": 4,
	"frappe / Workflow": 2,
	"hrms / HR": 0,
	"hrms / Payroll": 9,
	"onedesk / One": 1,
	"onedesk / One AI": 2,
	"onedesk / One Admin": 9,
	"onedesk / One Calendar": 1,
	"onedesk / One HR": 0,
	"onedesk / One Mail": 1,
	"onedesk / One Storage": 1,
	"onedesk / One Studio": 1,
}

#: Point 11. Documents sent to a customer or supplier on a print not ours.
UNPRINTED = {
	"erpnext / Accounts": 3,
	"erpnext / Maintenance": 1,
	"erpnext / Selling": 2,
	"erpnext / Subcontracting": 3,
}

#: Point 5. Lists that say nothing but a number.
ONLY_AN_ID = {
	"frappe / Core": 1,
}

#: Point 12. Labels on a reached form still English in Arabic or German,
#: counted once for each language.
ENGLISH = {
	"erpnext / Accounts": 54,
	"erpnext / Assets": 3,
	"erpnext / Buying": 21,
	"erpnext / CRM": 8,
	"erpnext / Manufacturing": 32,
	"erpnext / Projects": 40,
	"erpnext / Selling": 34,
	"erpnext / Setup": 34,
	"erpnext / Stock": 21,
	"erpnext / Subcontracting": 3,
	"erpnext / Support": 0,
	"frappe / Automation": 32,
	"frappe / Core": 26,
	"frappe / Desk": 33,
	"frappe / Email": 4,
	"frappe / Integrations": 6,
	"frappe / Printing": 6,
	"frappe / Website": 2,
	"hrms / HR": 0,
	"hrms / Payroll": 0,
}


def _point(check: str, allowed: dict) -> None:
	now = atlas.points()[check]
	grown = {m: names for m, names in now.items() if len(names) > allowed.get(m, 0)}
	assert not grown, f"{check} grew: {grown}"
	stale = {m: (len(now.get(m, [])), n) for m, n in allowed.items() if len(now.get(m, [])) < n}
	assert not stale, f"lower {check.upper()} (now, written): {stale}"


def test_the_demo_has_one_of_everything_reached():
	_point("empty", EMPTY)


def test_what_goes_out_prints_from_ours():
	_point("unprinted", UNPRINTED)


def test_a_list_says_more_than_a_number():
	_point("only_an_id", ONLY_AN_ID)


def test_what_is_reached_reads_in_every_language():
	_point("english", ENGLISH)


def test_the_points_are_read():
	"""The readers still work: the demo has items and a putaway rule but no
	stock dimension, an
	order prints from ours and the order sends Order Late."""
	assert atlas.kept("Item") and atlas.kept("Putaway Rule") and not atlas.kept("Inventory Dimension")
	assert atlas.goes_out("Purchase Order") and atlas.printed("Purchase Order")
	assert "Order Late" in atlas.sends("Purchase Order")
