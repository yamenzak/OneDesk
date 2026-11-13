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
HOOKS = tree.hooks()
LOGS = ("Version", "Activity Log", "Access Log")


def _body(name: str) -> str:
	return SOURCE.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]


def test_every_log_is_guarded_both_ways():
	"""Version's list runs audit's permission query; the two logs live in
	frappe's SQLite store, whose list runs none, so audit_logs puts the same
	limits on it as filters."""
	for doctype in LOGS:
		assert f'"{doctype}": "onedesk.one.audit.has_permission"' in HOOKS, doctype
	assert '"Version": "onedesk.one.audit.version_query"' in HOOKS
	held = (tree.APP / "one" / "audit_logs.py").read_text()
	for doctype, cls in (("Activity Log", "ActivityLog"), ("Access Log", "AccessLog")):
		assert f'"{doctype}": "onedesk.one.audit_logs.{cls}"' in HOOKS, doctype
		assert f"class {cls}(" in held and "def get_list(" in held and "def get_count(" in held
	assert "audit.SYSTEM" in held and "audit.kinds(audit.DOWNLOADS)" in held and "roles.administers(user)" in held
	assert '"onedesk.one.access.settle"' in HOOKS
	assert '"Version": {"onload": "onedesk.one.audit.onload"}' in HOOKS


def test_only_an_administrator_reads_and_nobody_writes():
	granted = tree.granted()
	for log in LOGS:
		assert not {"write", "delete", "create"} & set(granted[log]), log


def test_the_system_and_the_machinery_are_left_out():
	assert '"Administrator"' in SOURCE.split("SYSTEM = ", 1)[1].split("\n", 1)[0]
	kinds = _body("kinds")
	assert "get_doctypes_with_read()" in SOURCE and "REFUSED_MODULES" in kinds and '"istable": 1' in kinds


def test_a_change_shows_only_the_fields_its_reader_may_read():
	assert "row_hidden(table)" in _body("seen")
	assert "seen(doc.data, doc.ref_doctype)" in _body("onload")
	assert "audit.seen(one.data, one.ref_doctype)" in (tree.APP / "one" / "ai_workspace.py").read_text()


def test_accesscenter_reads_the_three_as_one_log():
	"""docs/ONE.md, stage 4: the three lists are one Audit Log in AccessCenter,
	each row opening frappe's own record; frappe's lists stay for that."""
	audit = (tree.APP / "one" / "audit.py").read_text()
	for doctype in ("Version", "Activity Log", "Access Log"):
		assert f'("{doctype}", [' in audit, doctype
	assert "roles.require()" in audit.split("def log(", 1)[1].split("\ndef ", 1)[0]
	centre = (tree.APP / "public" / "js" / "one" / "access_center.js").read_text()
	assert 'id: "audit"' in centre and 'audit." + "log"' in centre.replace('A.replace("access_center.", "audit.")', 'audit."')
	sidebar = json.loads((tree.APP / "one" / "sidebar" / "one" / "one.json").read_text())
	assert not {"Version", "Activity Log", "Access Log"} & {one.get("link_to") for one in sidebar["items"]}
	lists = (tree.APP / "public" / "js" / "one" / "audit_list.js").read_text()
	for title in ("Changes", "Sign-ins", "Exports and Prints"):
		assert f'headed(__("{title}"))' in lists, title
