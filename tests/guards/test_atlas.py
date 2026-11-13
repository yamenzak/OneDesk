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

WAITING = {
	"erpnext / Accounts": 0,
	"erpnext / Bulk Transaction": 0,
	"erpnext / Communication": 0,
	"erpnext / EDI": 0,
	"erpnext / ERPNext Integrations": 0,
	"erpnext / Maintenance": 0,
	"erpnext / Projects": 0,
	"erpnext / Quality Management": 0,
	"erpnext / Regional": 0,
	"erpnext / Selling": 0,
	"erpnext / Setup": 0,
	"erpnext / Support": 0,
	"erpnext / Telephony": 0,
	"erpnext / Utilities": 0,
	"frappe / Automation": 0,
	"frappe / Contacts": 0,
	"frappe / Core": 0,
	"frappe / Custom": 0,
	"frappe / Desk": 0,
	"frappe / Email": 0,
	"frappe / Integrations": 0,
	"frappe / Printing": 0,
	"frappe / Website": 0,
	"frappe / Workflow": 0,
	"hrms / HR": 0,
	"hrms / Payroll": 0,
}

KINDS = {"engine", "inside", "replaced", "left out", "the platform's"}


def grown(now: dict, allowed: dict) -> dict:
	"""What a count that only falls holds more of than allowed, `now` by key
	with its names. Pure."""
	return {key: names for key, names in now.items() if len(names) > allowed.get(key, 0)}


def stale(now: dict, allowed: dict) -> dict:
	"""(now, written) for each allowance higher than what it now holds. Pure."""
	return {key: (len(now.get(key, [])), n) for key, n in allowed.items() if len(now.get(key, [])) < n}


def out_of_date(written: str | None, drawn: str) -> bool:
	"""Whether a generated file is missing or not what is drawn now. Pure."""
	return written != drawn


def test_nothing_waits_that_was_not_waiting():
	now = {module: len(names) for module, names in atlas.waiting().items()}
	grown = {module: (n, WAITING.get(module, 0)) for module, n in now.items() if n > WAITING.get(module, 0)}
	assert not grown, (
		f"placed nowhere and not answered (now, allowed): {grown}. Place it or answer it in onedesk/one/atlas.py: { {m: atlas.waiting()[m] for m in grown} }"
	)


def test_the_counts_are_lowered_as_things_are_placed():
	found = stale(atlas.waiting(), WAITING)
	assert not found, f"lower WAITING to what is still waiting (now, written): {found}"


def test_every_answer_names_something_unreached():
	"""An answer for something the map now reaches, or that no longer exists,
	is a stale line."""
	found = stale_answers(atlas.rows(), atlas.answers())
	assert not found, found


def stale_answers(rows, said: dict) -> list[str]:
	"""An answer for nothing the map knows, for something it reaches, or of a
	kind not in KINDS. Pure."""
	reached = {(row["kind"], row["name"]) for row in rows if row["reach"]}
	known = {(row["kind"], row["name"]) for row in rows}
	out = [f"no such thing: {one}" for one in sorted(set(said) - known)]
	out += [f"reached now, take the answer out: {one}" for one in sorted(set(said) & reached)]
	out += [f"no such kind: {kind}" for kind in sorted({kind for kind, _ in said.values()} - KINDS)]
	return out


def test_the_map_finds_a_way_in():
	"""The reader of rails, links and Connections still works."""
	reach = atlas.reach()
	assert reach[("DocType", "Item")][0] == "named"
	assert reach[("DocType", "Warehouse Type")][0] == "linked"
	assert reach[("DocType", "Putaway Rule")][0] == "named"
	assert ("DocType", "Stock Reposting Settings") not in reach


def test_the_atlas_is_current():
	assert not out_of_date((atlas.tree.ROOT / "docs" / "ATLAS.md").read_text(), atlas.page()), "run python scripts/docs.py"


OPERATOR = ("One Admin",)

NOBODY = {
	"erpnext / Accounts": 0,
	"erpnext / Maintenance": 0,
	"erpnext / Selling": 0,
	"erpnext / Setup": 0,
	"erpnext / Support": 0,
	"frappe / Core": 8,
	"frappe / Custom": 1,
	"frappe / Desk": 0,
	"frappe / Email": 0,
	"frappe / Integrations": 0,
	"frappe / Website": 0,
	"frappe / Workflow": 0,
	"hrms / HR": 0,
	"onedesk / One": 0,
	"onedesk / One Sheet": 1,
	"onedesk / One Deck": 1,
	"onedesk / One AI": 0,
	"onedesk / One Mail": 0,
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
	assert not grown(now, NOBODY), f"reached, but no role a workspace gives may open it: {grown(now, NOBODY)}"
	assert not stale(now, NOBODY), f"lower NOBODY (now, written): {stale(now, NOBODY)}"


def test_who_may_open_what_was_read():
	"""docs/atlas-site.json was read from the site; a demo check holds it to
	the site's (one_atlas_knows_who_may_open_what)."""
	assert was_read(atlas.readers()), "run python scripts/atlas.py --site"


def was_read(readers: dict) -> bool:
	"""Whether the site's readers were read: Item has some. Pure."""
	return bool(readers["doctypes"].get("Item"))


def test_the_brand_translations_are_current():
	for lang, text in atlas.translation_files().items():
		path = atlas.TRANSLATIONS / f"{lang}.csv"
		assert not out_of_date(path.read_text() if path.exists() else None, text), f"run python scripts/atlas.py --brand ({lang})"


def _unbranded(text: str, outside) -> str:
	for name in outside:
		text = text.replace(name, "")
	return text


def still_branded(brand, said: dict, outside) -> list:
	"""Each upstream sentence naming frappe, erpnext or hrms that One does not
	swap, and each swap still naming one, but for an outside name. Pure."""
	swapped = {msgid for msgid, _, _ in said["en"]}
	out = [msgid for msgid in brand if msgid not in swapped and atlas.SAID_BRAND.search(_unbranded(msgid, outside))]
	out += [(lang, msgid, text) for lang, rows in said.items() for msgid, text, _ in rows if atlas.SAID_BRAND.search(_unbranded(text, outside))]
	return out


def test_nothing_upstream_says_names_them():
	"""Every sentence frappe, erpnext or hrms say naming themselves reads One,
	in English, Arabic and German, but for an outside name kept on purpose."""
	found = still_branded(atlas.upstream()["brand"], atlas.rebranded(), atlas._module_dict("OUTSIDE"))
	assert not found, found


UNHEARD = {
	# OneCloud hears its own event in File's room, onecloud_change
	# (one_cloud/live.py), sent for every change to a file, its versions and
	# its shares; what its preview reads beside a file (versions, comments,
	# shares, what OneAI read and did) is read again each time a file is
	# chosen. A project's and an item's Files are OneCloud.
	"onecloud": 5,
	"project_part": 1,
	# OneMail hears its own event, onemail_change (one_mail/live.py), which
	# names the mailbox a sync or an action changed; a list follow on
	# Communication would wake it for every mail in the workspace.
	"onemail": 6,
	# The presentation editor reads the workspace's fonts, Files in OneCloud ›
	# Fonts, once when it opens and again after it adds one (one_deck/fonts.py).
	"presentation": 1,
}

BARE = {}

NOT_THE_COMPANYS = {
	"project_part": 4,
}


def _held(key: str, allowed: dict) -> None:
	now = {one["screen"]: one[key] for one in atlas.screens() if one[key]}
	assert not grown(now, allowed), f"{key} grew: {grown(now, allowed)}"
	assert not stale(now, allowed), f"lower the count (now, written): {stale(now, allowed)}"


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


EMPTY = {
	# a screen comes only from a TV opening /tv (one_display/AGENTS.md)
	"onedesk / One Display": 0,
	"erpnext / Regional": 3,
	"erpnext / Accounts": 23,
	"erpnext / Assets": 2,
	"erpnext / CRM": 1,
	"erpnext / Maintenance": 0,
	"erpnext / Manufacturing": 4,
	"erpnext / Projects": 1,
	"erpnext / Selling": 4,
	"erpnext / Setup": 4,
	"erpnext / Stock": 6,
	"erpnext / Subcontracting": 1,
	"erpnext / Support": 0,
	"frappe / Automation": 1,
	"frappe / Core": 0,
	"frappe / Desk": 0,
	"frappe / Email": 2,
	"frappe / Integrations": 3,
	"frappe / Website": 0,
	"frappe / Workflow": 0,
	"hrms / HR": 0,
	"hrms / Payroll": 9,
	"onedesk / One": 0,
	"onedesk / One AI": 0,
	"onedesk / One Admin": 14,
	"onedesk / One Calendar": 1,
	"onedesk / One HR": 0,
	"onedesk / One Mail": 0,
	"onedesk / One Cloud": 0,
	"onedesk / One Studio": 1,
}

UNPRINTED = {
	"erpnext / Accounts": 0,
	"erpnext / Maintenance": 0,
	"erpnext / Selling": 0,
	"erpnext / Subcontracting": 0,
}

ONLY_AN_ID: dict = {}

ENGLISH: dict = {}


def _point(check: str, allowed: dict) -> None:
	now = atlas.points()[check]
	assert not grown(now, allowed), f"{check} grew: {grown(now, allowed)}"
	assert not stale(now, allowed), f"lower {check.upper()} (now, written): {stale(now, allowed)}"


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


def test_the_counts_catch_their_examples():
	"""A count that grew, a count left higher than what it holds, and one held."""
	assert grown({"onemail": ["Communication", "Contact"]}, {"onemail": 1}) == {"onemail": ["Communication", "Contact"]}
	assert stale({"onemail": ["Communication"]}, {"onemail": 2, "stock": 1}) == {"onemail": (1, 2), "stock": (0, 1)}
	assert not grown({"stock": ["Bin"]}, {"stock": 1}) and not stale({"stock": ["Bin"]}, {"stock": 1})


def test_the_answers_and_the_generated_files_catch_their_examples():
	rows = [{"kind": "DocType", "name": "Item", "reach": "named"}, {"kind": "DocType", "name": "Bin", "reach": ""}]
	said = {("DocType", "Item"): ("engine", ""), ("DocType", "Gone"): ("engine", ""), ("DocType", "Bin"): ("whim", "")}
	assert stale_answers(rows, said) == [
		"no such thing: ('DocType', 'Gone')",
		"reached now, take the answer out: ('DocType', 'Item')",
		"no such kind: whim",
	]
	assert not stale_answers(rows, {("DocType", "Bin"): ("inside", "")})
	assert out_of_date(None, "x") and out_of_date("old", "new") and not out_of_date("same", "same")
	assert not was_read({"doctypes": {}}) and was_read({"doctypes": {"Item": ["Stock User"]}})
	said = {"en": [("Open ERPNext", "Open One", "")], "ar": [("Open ERPNext", "افتح ERPNext", "")]}
	assert still_branded(["Open ERPNext", "Frappe HR", "Paid via Stripe"], said, ["Stripe"]) == ["Frappe HR", ("ar", "Open ERPNext", "افتح ERPNext")]
	assert not still_branded(["Paid via Frappe Cloud"], {"en": []}, ["Frappe Cloud"])
