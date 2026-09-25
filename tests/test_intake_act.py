"""Intake, stage 4: the one door, and where a document is filed."""

import ast
import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "onedesk" / "one_intake"


def _cint(value):
	try:
		return int(float(value or 0))
	except (TypeError, ValueError):
		return 0


def _flt(value, precision=None):
	try:
		return float(value if value is not None else 0)
	except (TypeError, ValueError):
		return 0.0


def _getdate(value):
	return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def _load(path: Path, space: dict, names: set) -> dict:
	for node in ast.parse(path.read_text()).body:
		named = getattr(node, "name", None) or (getattr(node.targets[0], "id", None) if isinstance(node, ast.Assign) else None)
		if named in names:
			exec(ast.unparse(node), space)
	return space


ACT = _load(
	ROOT / "act.py",
	{"dataclass": dataclass, "field": field, "hashlib": hashlib, "json": json, "cint": _cint, "flt": _flt},
	{"KINDS", "FLOOR", "CHANGES", "Action", "level", "key_of", "_filled", "_same"},
)
import re  # noqa: E402

FILING = _load(
	ROOT / "filing.py",
	{"Action": ACT["Action"], "re": re, "getdate": _getdate, "today": lambda: "2026-09-24", "cint": _cint},
	{"CERTAIN", "ROLES", "PERSONAL_RECORDS", "JUNK", "BULK", "NAMED", "UNSAFE", "MOST_NAME", "records", "party_of", "file_name", "plan"},
)
Action = ACT["Action"]

SUPPLIER = {"role": "Sender", "party_name": "Stadtwerke Köln GmbH", "matched_doctype": "Supplier", "matched_name": "Stadtwerke Köln GmbH", "score": 0.99}
US = {"role": "Recipient", "party_name": "Acme GmbH", "ours": "Company", "score": 0}
INVOICE = {"name": "r1", "kind": "Invoice", "verdict": "Action", "title": "Stadtwerke Köln GmbH RE-2026-0042", "issued_on": "2026-09-01", "sensitivity": "Ordinary", "parties": [SUPPLIER, US]}
DROPPED = {"file": "f1", "file_name": "scan_0001", "extension": "pdf", "folder": "Home/Post", "own": False, "attached": None, "switched": "Home/Post", "kind_label": "Rechnung", "today": "2026-09-24", "tags": ["Rechnung", "2026", "OneAI"], "file_away": True}


def kinds(actions):
	return [(one.kind, one.doctype, one.name) for one in actions]


# ------------------------------------------------------------------ the door


def test_what_waits_for_a_person():
	level = ACT["level"]
	assert level(Action("Update", "Supplier", "S", {"tax_id": "DE2"}), {}, {"tax_id": "DE1"})[:2] == ("Proposed", "overwrite")
	assert level(Action("Update", "Supplier", "S", {"tax_id": "DE1"}), {}, {"tax_id": "DE1"})[0] == "Done", "the same value is no overwrite"
	assert level(Action("Update", "Supplier", "S", {"website": "x.de"}), {}, {"website": None})[0] == "Done", "an empty field is filled"
	assert level(Action("Update", "Employee", "E", {"relieving_date": "2026-10-01"}, ends_employment=True), {}, {})[:2] == ("Proposed", "employment")
	assert level(Action("Create", "Supplier", confidence=0.5), {}, {})[:2] == ("Proposed", "unsure")
	assert level(Action("Create", "Supplier"), {"unsure": 1}, {})[:2] == ("Done", ""), "a dropped fact is not used, so it holds nothing up"
	assert level(Action("Create", "File", sure=True, confidence=0.1), {"unsure": 1}, {})[0] == "Done", "cutting a batch is not a judgement"
	assert level(Action("Link", "Supplier", "S", {"file": "f"}), {"unsure": 1}, {})[0] == "Done", "filing is not held back by doubts"
	assert level(Action("Update", "Supplier", "S", {"credit": 100}), {}, {"credit": 100.0})[0] == "Done", "numbers compare as numbers"


def test_an_action_is_keyed_by_what_it_does():
	key_of = ACT["key_of"]
	one = key_of("hash", Action("Update", "Supplier", "S", {"a": 1, "b": 2}))
	assert one == key_of("hash", Action("Update", "Supplier", "S", {"b": 2, "a": 1}))
	assert one != key_of("hash", Action("Update", "Supplier", "S", {"a": 2, "b": 2}))
	assert key_of("hash", Action("Tag", "File", "f", key="given")) == "given"


# ------------------------------------------------------------------ names


def test_a_file_is_named_by_its_day_party_and_kind():
	name = FILING["file_name"]
	assert name(date(2026, 9, 24), "Stadtwerke Köln", "Mahnung", "Mahnung Strom", "pdf") == "2026-09-24 Stadtwerke Köln – Mahnung Strom.pdf"
	assert name(date(2026, 9, 1), "Stadtwerke Köln GmbH", "Invoice", "Stadtwerke Köln GmbH RE-2026-0042", "xml") == "2026-09-01 Stadtwerke Köln GmbH – Invoice RE-2026-0042.xml"
	assert name(date(2026, 9, 1), "", "Receipt", "Coffee", "jpg") == "2026-09-01 Receipt Coffee.jpg"
	assert "/" not in name(date(2026, 9, 1), "A/B GmbH", "Invoice", 'x:y"z', "pdf")
	assert len(name(date(2026, 9, 1), "P" * 80, "Invoice", "T" * 200, "pdf")) <= FILING["MOST_NAME"] + 4


def test_the_record_a_document_belongs_to_comes_first():
	records = FILING["records"]
	employee = {"role": "Holder", "matched_doctype": "Employee", "matched_name": "E1", "score": 0.95}
	guess = {"role": "Mentioned", "matched_doctype": "Customer", "matched_name": "C1", "score": 0.6}
	assert records([SUPPLIER, employee, guess, US]) == [("Employee", "E1"), ("Supplier", "Stadtwerke Köln GmbH")]
	assert records([SUPPLIER, SUPPLIER]) == [("Supplier", "Stadtwerke Köln GmbH")]


# ------------------------------------------------------------------ filing a file


def test_a_matched_invoice_is_filed_with_its_supplier():
	plan = FILING["plan"](INVOICE, DROPPED)
	assert kinds(plan) == [("Attach", "Supplier", "Stadtwerke Köln GmbH"), ("Rename", "File", "f1"), ("Tag", "File", "f1")]
	assert plan[1].values["file_name"] == "2026-09-01 Stadtwerke Köln GmbH – Rechnung RE-2026-0042.pdf"
	assert all(one.sure for one in plan)


def test_an_unmatched_document_goes_to_its_kind_and_year():
	reading = {**INVOICE, "parties": [{**SUPPLIER, "matched_doctype": None, "matched_name": None, "score": 0}]}
	plan = FILING["plan"](reading, DROPPED)
	assert kinds(plan) == [("Rename", "File", "f1"), ("Move", "File", "f1"), ("Tag", "File", "f1")]
	assert plan[1].values == {"under": "Home/Post", "path": ["Rechnung", "2026"]}
	assert kinds(FILING["plan"](reading, {**DROPPED, "file_away": False})) == [("Rename", "File", "f1"), ("Tag", "File", "f1")]


def test_a_file_in_my_files_is_only_linked_and_tagged():
	plan = FILING["plan"](INVOICE, {**DROPPED, "own": True})
	assert kinds(plan) == [("Link", "Supplier", "Stadtwerke Köln GmbH"), ("Tag", "File", "f1")]


def test_a_file_a_person_attached_stays_where_they_put_it():
	plan = FILING["plan"](INVOICE, {**DROPPED, "attached": ["Project", "P1"], "switched": None})
	assert ("Attach", "Supplier", "Stadtwerke Köln GmbH") not in kinds(plan)
	assert ("Link", "Supplier", "Stadtwerke Köln GmbH") in kinds(plan)
	assert not any(one.kind == "Move" for one in plan)


def test_a_mail_attachment_is_copied_to_its_record_under_its_new_name():
	plan = FILING["plan"](INVOICE, {**DROPPED, "attached": ["Communication", "c1"], "switched": None})
	assert kinds(plan) == [("Attach", "Supplier", "Stadtwerke Köln GmbH"), ("Tag", "File", "f1")]
	assert plan[0].values["file_name"].startswith("2026-09-01 Stadtwerke"), "the mail keeps its own name for it"


def test_a_sensitive_document_is_attached_only_to_its_person():
	sick = {**INVOICE, "kind": "Sick Note", "sensitivity": "Medical"}
	assert ("Attach", "Supplier", "Stadtwerke Köln GmbH") not in kinds(FILING["plan"](sick, DROPPED))
	holder = {"role": "Holder", "matched_doctype": "Employee", "matched_name": "HR-EMP-1", "score": 0.97}
	plan = FILING["plan"]({**sick, "parties": [holder, SUPPLIER]}, DROPPED)
	assert kinds(plan)[:2] == [("Attach", "Employee", "HR-EMP-1"), ("Link", "Supplier", "Stadtwerke Köln GmbH")]


def test_a_named_file_keeps_its_name():
	plan = FILING["plan"](INVOICE, {**DROPPED, "file_name": "2026-08-30 Strom"})
	assert not any(one.kind == "Rename" for one in plan)


def test_junk_through_a_trusted_channel_is_set_aside():
	advert = {**INVOICE, "verdict": "Advertising", "kind": None}
	plan = FILING["plan"](advert, DROPPED)
	assert kinds(plan) == [("Move", "File", "f1")] and plan[0].values["path"] == ["Advertising"]
	assert FILING["plan"]({**INVOICE, "verdict": "Phishing"}, DROPPED) == [], "phishing is warned about, never filed"
	assert FILING["plan"](advert, {**DROPPED, "own": True}) == []


# ------------------------------------------------------------------ filing a message

MAIL = {"message": "c1", "direct": True, "in_inbox": True, "junk": "JUNK-1", "newsletters": None, "newsletters_label": "Newsletter", "today": "2026-09-24"}


def test_a_message_is_linked_to_every_record_it_is_about():
	assert kinds(FILING["plan"](INVOICE, MAIL)) == [("Link", "Supplier", "Stadtwerke Köln GmbH")]


def test_junk_that_came_straight_in_leaves_the_inbox():
	spam = FILING["plan"]({**INVOICE, "verdict": "Spam"}, MAIL)
	assert kinds(spam) == [("Move", "Communication", "c1")] and spam[0].values == {"mail_folder": "JUNK-1"}
	news = FILING["plan"]({**INVOICE, "verdict": "Newsletter"}, MAIL)
	assert news[0].values == {"mail_folder_label": "Newsletter"}
	assert ("Link", "Supplier", "Stadtwerke Köln GmbH") in kinds(news), "a newsletter is filed with its sender"
	assert FILING["plan"]({**INVOICE, "verdict": "Spam"}, {**MAIL, "direct": False}) == [], "a colleague's forward stays where they put it"
	assert FILING["plan"]({**INVOICE, "verdict": "Spam"}, {**MAIL, "in_inbox": False}) == [], "a rule already moved it"


def test_filing_writes_only_through_the_door():
	source = (ROOT / "filing.py").read_text()
	for node in ast.parse(source).body:
		if isinstance(node, ast.FunctionDef) and node.name not in ("cut", "forget"):
			said = ast.unparse(node)
			for write in (".insert(", ".save(", "db.set_value(", "delete_doc(", "db.delete("):
				assert write not in said, f"{node.name} writes with {write}; it should plan an Action"


def test_the_mark_is_taken_down_by_a_person_and_nothing_else():
	hooks = (ROOT.parent / "hooks.py").read_text()
	for event in ("on_update", "on_submit", "on_cancel"):
		assert re.search(rf'"{event}": \[?[^\]]*"onedesk\.one_intake\.mark\.looked_at"', hooks), event
	assert '"before_rename": "onedesk.one_intake.mark.before_rename"' in hooks
	source = (ROOT / "mark.py").read_text()
	assert "one_intake_writing" in source and "in_import" in source, "OneAI's own writes and imports do not count as looking"
	assert '"Intake Action": "onedesk.one_intake.act.query"' in hooks and '"Intake Action": "onedesk.one_intake.act.has_permission"' in hooks
