"""The Audit Log (one/audit.py): frappe's own changes, sign-ins and exports,
read by a workspace administrator only, of the kinds of record they may read,
never the system's own, and a change without the fields they may not read.
These read the code that says so."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SOURCE = (tree.APP / "one" / "audit.py").read_text()
HOOKS = (tree.APP / "hooks.py").read_text()
LOGS = ("Version", "Activity Log", "Access Log")


def _body(name: str) -> str:
	return SOURCE.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]


def test_every_log_is_guarded_both_ways():
	for doctype, query in zip(LOGS, ("version_query", "activity_query", "access_query"), strict=True):
		assert f'"{doctype}": "onedesk.one.audit.has_permission"' in HOOKS, doctype
		assert f'"{doctype}": "onedesk.one.audit.{query}"' in HOOKS, doctype
	assert '"onedesk.one.audit.settle"' in HOOKS
	assert '"Version": {"onload": "onedesk.one.audit.onload"}' in HOOKS


def test_only_an_administrator_reads_and_nobody_writes():
	for query in ("version_query", "activity_query", "access_query"):
		assert 'return "1=0"' in _body(query), query
	allowed = _body("has_permission")
	assert 'ptype not in ("read", "report", None)' in allowed and "roles.administers(user)" in allowed
	grants = SOURCE.split("GRANTS = {", 1)[1].split("}", 1)[0]
	assert "write" not in grants and "delete" not in grants and "create" not in grants


def test_the_system_and_the_machinery_are_left_out():
	assert '"Administrator"' in SOURCE.split("SYSTEM = ", 1)[1].split("\n", 1)[0]
	for query in ("version_query", "activity_query", "access_query"):
		assert "_not_system(" in _body(query), query
	kinds = _body("kinds")
	assert "get_doctypes_with_read()" in SOURCE and "REFUSED_MODULES" in kinds and '"istable": 1' in kinds


def test_a_change_shows_only_the_fields_its_reader_may_read():
	assert 'get_permlevel_access("read"' in _body("_unseen")
	seen = _body("seen")
	assert "not in unseen" in seen and "row_hidden(table)" in seen
	assert "seen(doc.data, doc.ref_doctype)" in _body("onload")
	assert "audit.seen(one.data, one.ref_doctype)" in (tree.APP / "one" / "ai.py").read_text()


def test_the_sidebar_names_the_three_lists():
	sidebar = json.loads((tree.APP / "one" / "sidebar" / "one" / "one.json").read_text())
	links = {one["link_to"]: one["label"] for one in sidebar["items"] if one.get("link_type") == "DocType"}
	assert links["Version"] == "Changes"
	assert links["Activity Log"] == "Sign-ins"
	assert links["Access Log"] == "Exports and Prints"
	lists = (tree.APP / "public" / "js" / "audit_list.js").read_text()
	for title in ("Changes", "Sign-ins", "Exports and Prints"):
		assert f'headed(__("{title}"))' in lists, title
