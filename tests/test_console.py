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


def test_both_gates_are_registered_on_every_owned_doctype():
	"""One hook is not enough, and that was measured rather than assumed.

	`has_permission` is called only when Frappe has a document to judge, so on
	its own it guarded opening a record and left `get_list` wide open — with the
	operator role granted by hand and the flag off, a Tenant list still returned
	rows. `permission_query_conditions` is the seam every list, report and link
	search passes through.
	"""
	import re

	hooks = (tree.APP / "hooks.py").read_text(encoding="utf-8")
	owned = _owned()
	for hook, fn in (
		("has_permission", "refuse_on_a_tenant"),
		("permission_query_conditions", "nothing_on_a_tenant"),
	):
		block = re.search(rf"^{hook} = \{{(.*?)^\}}", hooks, re.S | re.M)
		assert block, f"{hook} is not declared in hooks.py"
		named = set(re.findall(r'"([^"]+)": "onedesk\.one_admin\.site\.' + fn, block.group(1)))
		assert owned <= named, f"{hook} misses {sorted(owned - named)}"


def test_the_console_wears_its_own_mark():
	"""OneAdmin is its own product with its own mark; `one` is a different one."""
	assert _sidebar()["header_icon"] == "oneadmin"
	assert _workspace()["icon"] == "oneadmin"
	shipped = json.loads(
		(tree.APP / "fixtures" / "custom_icon.json").read_text(encoding="utf-8")
	)
	assert "oneadmin" in {one["name"] for one in shipped}


def test_the_console_has_its_own_row_in_the_dock():
	"""Reachable by clicking rather than by knowing the URL.

	It is last on purpose: the four above it are opened every day and this one
	is opened by two people.
	"""
	dock = _json(tree.APP / "dock" / "onedesk" / "onedesk.json")
	rows = {row["link_to"]: row for row in dock["items"]}
	assert "One Admin" in rows, "the dock does not offer the console"
	assert rows["One Admin"]["icon"] == "oneadmin"
	assert rows["One Admin"]["link_type"] == "Sidebar"
	assert dock["items"][-1]["link_to"] == "One Admin"


def test_nothing_on_a_workspace_is_typed():
	"""Every field is the record of something that happened, not a setting.

	The one that mattered: Status was a live Select, so an operator could drop a
	workspace from a dropdown — no job, no call to press, no R2 sweep, and a
	record saying the files were gone while the files were still there.
	"""
	doc = _json(ADMIN / "doctype" / "tenant" / "tenant.json")
	typed = [
		one["fieldname"]
		for one in doc["fields"]
		if one["fieldtype"] not in ("Section Break", "Column Break", "Tab Break")
		and not one.get("read_only")
	]
	assert not typed, f"{typed} can be typed on a Tenant"
	for perm in doc["permissions"]:
		assert not perm.get("write"), "a Tenant can be saved, so the form offers Save"
		assert not perm.get("delete"), "a Tenant can be deleted"


def test_the_form_carries_no_essays():
	"""A field description is a sentence, not a paragraph from a commit message.

	This file's first version put the whole reasoning for the ladder under the
	Status select, four lines of it, on a screen somebody opens to find out
	whether a customer is paying.
	"""
	doc = _json(ADMIN / "doctype" / "tenant" / "tenant.json")
	long = {
		one["fieldname"]: len(one["description"])
		for one in doc["fields"]
		if len(one.get("description") or "") > 120
	}
	assert not long, f"these descriptions belong in docs/ rather than on the form: {long}"


def test_every_operator_verb_is_gated():
	"""Both gates, on every whitelisted method, without exception.

	`_may` is `require_admin` plus `only_for`. A verb that forgot it would be a
	workspace anybody with a desk login could archive.
	"""
	import ast

	source = (ADMIN / "operator.py").read_text(encoding="utf-8")
	for node in ast.parse(source).body:
		if not isinstance(node, ast.FunctionDef):
			continue
		whitelisted = any(
			isinstance(one, ast.Attribute) and one.attr == "whitelist"
			for one in node.decorator_list
		)
		if not whitelisted:
			continue
		calls = {
			one.func.id
			for one in ast.walk(node)
			if isinstance(one, ast.Call) and isinstance(one.func, ast.Name)
		}
		assert "_may" in calls, f"{node.name} is whitelisted and does not call _may()"


def test_an_operator_may_only_send_a_workspace_to_a_real_rung():
	"""Read from the AST: `operator.py` imports frappe and this suite has none.

	`ladder.py` does not, which is the point of it being pure — so the rungs
	come from the module and the buttons come from the file.
	"""
	import ast

	from onedesk.one_admin import ladder

	source = (ADMIN / "operator.py").read_text(encoding="utf-8")
	by_hand = None
	for node in ast.parse(source).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "BY_HAND":
			by_hand = {key.value: value.value for key, value in zip(node.value.keys, node.value.values)}
	assert by_hand, "operator.py declares no BY_HAND"

	assert set(by_hand) <= set(ladder.RUNGS)
	assert "Live" not in by_hand, "climbing back is `restore`, not a fall"
	for rung, warning in by_hand.items():
		if rung in ("Suspended", "Archived", "Dropped"):
			assert warning, f"{rung} costs somebody something and says nothing about it"
