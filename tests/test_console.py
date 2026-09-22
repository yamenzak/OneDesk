"""The operator console, read back from the files rather than from a site.

Three of these are about a rail going wrong quietly. A sidebar naming a doctype
that does not exist renders an entry that 404s; a doctype nobody put in the rail
is reachable only by typing its name into the awesomebar, which is how the seven
One Admin doctypes were reached before this stage existed.

One is about something worse. The console is hidden by one thing and one thing
only — every One Admin document grants `One Operator` and `site.apply` strips
that role from every user on a workspace site. A workspace page that forgot its
`roles` would put the whole operator console in every tenant's dock.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

ADMIN = tree.APP / "one_admin"
OPERATOR = "One Operator"

#: One Admin's own doctypes that are deliberately not in the rail, and why.
#: Anything else missing from it is an oversight rather than a decision.
UNRAILED = {
	# Stripe's deliveries and the unique index that makes a redelivery harmless.
	# There is nothing to do on this screen; it is read when a payment is being
	# chased, by somebody who will type its name.
	"Stripe Webhook Event",
}

#: Records made by the machinery that also fills them in. An operator typing one
#: gets a half-record every screen then reads as though it were real.
MADE_FOR_YOU = {
	"Tenant",
	"Provisioning Job",
	"Tenant Domain",
	"Tenant Event",
	"Account Request",
	"Stripe Webhook Event",
}


def _json(path: Path) -> dict:
	return json.loads(path.read_text(encoding="utf-8"))


def _sidebar() -> dict:
	return _json(ADMIN / "sidebar" / "one_admin" / "one_admin.json")


def _workspace() -> dict:
	return _json(ADMIN / "workspace" / "one_admin" / "one_admin.json")


def _owned() -> set[str]:
	"""Every doctype the One Admin module ships."""
	folder = ADMIN / "doctype"
	return {
		_json(one / f"{one.name}.json")["name"]
		for one in folder.iterdir()
		if one.is_dir() and (one / f"{one.name}.json").exists()
	}


def test_the_console_is_gated_on_the_operator_role():
	"""The whole of the hiding, and the only thing standing between a tenant and it."""
	roles = [row["role"] for row in _workspace().get("roles") or []]
	assert roles == [OPERATOR], f"the One Admin page grants {roles}"


def test_every_rail_entry_points_at_something_real():
	rail = _sidebar()["items"]
	owned = _owned()
	for item in rail:
		if item.get("link_type") != "DocType":
			continue
		assert item["link_to"] in owned, (
			f"the rail names {item['link_to']!r}, which One Admin does not own"
		)


def test_the_rail_starts_at_home():
	first = _sidebar()["items"][0]
	assert first["link_type"] == "Workspace"
	assert first["link_to"] == "One Admin"


def test_nothing_is_reachable_only_by_typing_its_name():
	rail = {i.get("link_to") for i in _sidebar()["items"] if i.get("link_type") == "DocType"}
	missing = sorted(_owned() - rail - UNRAILED)
	assert not missing, (
		f"{missing} are One Admin's and are in no rail entry. Add them, or say in "
		"UNRAILED why an operator should have to type the name."
	)


def test_the_home_page_names_number_cards_that_exist():
	shipped = {
		_json(one / f"{one.name}.json")["name"]
		for one in (ADMIN / "number_card").iterdir()
		if one.is_dir()
	}
	named = {row["number_card_name"] for row in _workspace().get("number_cards") or []}
	assert named <= shipped, f"the home page names cards that do not exist: {named - shipped}"


def test_a_record_the_machinery_makes_cannot_be_typed_by_hand():
	"""An operator-made Tenant has no site, no token and no job behind it.

	Every one of these is inserted with `ignore_permissions`, so withdrawing
	create costs the machinery nothing and closes the button that makes a record
	the rest of the code then believes.
	"""
	for name in sorted(MADE_FOR_YOU):
		folder = name.lower().replace(" ", "_")
		doc = _json(ADMIN / "doctype" / folder / f"{folder}.json")
		for perm in doc["permissions"]:
			assert not perm.get("create"), f"{name} can be created by hand"


def test_an_offering_can_be_typed_by_hand():
	"""The exception, and the reason the rule above is a list rather than a sweep.

	A price list is exactly the thing an operator writes.
	"""
	doc = _json(ADMIN / "doctype" / "offering" / "offering.json")
	assert any(perm.get("create") for perm in doc["permissions"])
