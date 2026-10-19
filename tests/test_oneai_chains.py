"""OneAI makes several things that belong together in one step, mends its own
calls from what an error says, and marks everything it put into a record.

A card may point at the record another card will make ("@PROP-26-000042"),
so a new customer and a quotation for them are two cards suggested at once;
approving the quotation approves the customer first. A readiness check makes
the record exactly as Approve will, inside a savepoint it always rolls back,
so a quotation is not refused for a currency the insert would have filled.
An error is answered with what mends it rather than the code's own message,
and a card that fails at Approve goes back to OneAI to be corrected.
"""

import ast
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

AI = tree.APP / "one_ai"
JS = tree.APP / "public" / "js"


def _source(where: Path, name: str) -> str:
	for node in ast.walk(ast.parse(where.read_text(encoding="utf-8"))):
		if isinstance(node, (ast.FunctionDef, ast.Assign)) and (
			getattr(node, "name", None) == name
			or any(getattr(t, "id", None) == name for t in getattr(node, "targets", []))
		):
			return ast.unparse(node)
	raise AssertionError(f"{name} is not in {where.name}")


def _lifted(where: Path, names: tuple, room: dict) -> dict:
	"""Pure functions out of a module that imports frappe."""
	body = ast.parse(where.read_text(encoding="utf-8"))
	kept = [
		node
		for node in body.body
		if (isinstance(node, ast.FunctionDef) and node.name in names)
		or (isinstance(node, ast.Assign) and any(getattr(t, "id", None) in names for t in node.targets))
	]
	exec(compile(ast.Module(body=kept, type_ignores=[]), str(where), "exec"), room)
	return room


def test_a_value_may_point_at_a_card():
	import re

	room = _lifted(AI / "kind.py", ("REF", "refs", "resolved"), {"re": re})
	changes = {
		"party_name": "@PROP-26-000042",
		"items": [{"item_code": "A", "against": "@PROP-26-000043"}],
		"title": "@nobody",
	}
	assert room["refs"](changes) == ["PROP-26-000042", "PROP-26-000043"]
	made = room["resolved"](changes, {"PROP-26-000042": "Acme", "PROP-26-000043": "SO-1"})
	assert made["party_name"] == "Acme" and made["items"][0]["against"] == "SO-1"
	assert made["title"] == "@nobody", "only a card's id is a pointer"


def test_approving_a_card_approves_what_it_points_at_first():
	propose = _source(AI / "proposals.py", "propose")
	assert "_chained(" in propose and "'needs'" in propose
	apply = _source(AI / "proposals.py", "apply")
	assert apply.index("_made_first(entry)") < apply.index("entry.kind == 'Customize'")
	first = _source(AI / "proposals.py", "_made_first")
	assert "apply(card)" in first
	chained = _source(AI / "proposals.py", "_chained")
	assert "asked_by != frappe.session.user" in chained, "a card may point only at the asker's own"


def test_several_records_are_one_step():
	tools = (AI / "tools.py").read_text(encoding="utf-8")
	assert "def create_records(" in tools
	assert "SUGGESTS = (create_record, create_records," in tools
	groups = (AI / "groups.py").read_text(encoding="utf-8")
	assert '"create_records"' in groups[: groups.index("GROUPS")], "every request is given create_records"
	run = (AI / "run.py").read_text(encoding="utf-8")
	assert "def _cards(" in run and "'cards'" in _source(AI / "run.py", "_cards")


def test_ready_makes_the_record_as_approve_will_and_rolls_it_back():
	ready = _source(AI / "kind.py", "ready")
	assert "doc.insert()" in ready
	assert "first.insert()" in ready, "the cards it points at are made first"
	at = ready.index("finally:")
	assert "frappe.db.rollback(save_point=READY)" in ready[at:], "always rolled back"
	assert "run_method('validate')" not in ready, "validate alone misses what insert fills in"


def test_the_panel_approves_them_all_and_hands_a_failure_back():
	panel = (JS / "oneai" / "Panel.vue").read_text(encoding="utf-8")
	assert "onedesk.one_ai.run.apply_all" in panel and "Approve All" in panel
	assert '@failed="mend"' in panel and "function mend(" in panel
	record = (JS / "oneai" / "Record.vue").read_text(encoding="utf-8")
	assert 'emit("failed"' in record


def test_an_error_is_answered_with_what_mends_it():
	tried = _source(AI / "run.py", "_tried")
	assert "heal.said(" in tried and "heal.unknown(" in tried
	assert "[:500]" not in tried

	room = _lifted(
		AI / "heal.py",
		("_arguments", "_about_arguments", "_near", "unknown"),
		{"inspect": inspect, "re": __import__("re")},
	)

	def create_record(doctype, values, why=None):
		pass

	said = room["_arguments"]("create_record", create_record, {"doctyp": "Customer"})
	assert "takes doctype (needed), values (needed), why" in said
	assert "no doctyp" in said and "needs doctype, values" in said
	assert room["_about_arguments"]("create_record() got an unexpected keyword argument 'doctyp'")
	assert "create_record" in room["unknown"]("make_record", ["create_record", "read_record", "how_to"])


def test_a_refusal_says_not_to_try_again():
	heal = (AI / "heal.py").read_text(encoding="utf-8")
	said = _source(AI / "heal.py", "said")
	assert said.index("PermissionError") < said.index("ValidationError"), "a refusal is not something to mend"
	assert "do not try again" in heal


def test_every_field_oneai_set_is_marked_and_so_is_a_record_it_made():
	touch = (AI / "touch.py").read_text(encoding="utf-8")
	wrote = _source(AI / "touch.py", "wrote")
	assert "UNMARKED" in wrote and "TEXTS" not in wrote, "a date or an amount it set is marked too"
	same = _source(AI / "touch.py", "same")
	assert "flt(one) == flt(other)" in same, "100 and 100.0 are one value"
	assert '"ai_made"' in touch
	oneai = (JS / "oneai.js").read_text(encoding="utf-8")
	assert "onedesk.oneai.made = function" in oneai and "onedesk.oneai.made(frm)" in oneai
	assert "Made by {0}" in oneai


def test_what_earlier_questions_read_is_sent_cut_down_and_kept_whole():
	room = _lifted(AI / "chat.py", ("EARLIER_ROWS", "EARLIER_TEXT", "lighter", "_cut", "_whole"), {})
	rows = [{"name": str(n)} for n in range(30)]
	turns = [
		{"role": "user", "text": "first"},
		{"role": "tool", "id": "a", "result": rows},
		{"role": "model", "text": "thirty"},
		{"role": "user", "text": "second"},
		{"role": "tool", "id": "b", "result": rows},
	]
	sent = room["lighter"](turns)
	assert len(sent[1]["result"]) == room["EARLIER_ROWS"] + 1 and sent[1]["result"][-1] == {"left_out": 25}
	assert sent[4]["result"] == rows, "what answers this question goes whole"
	assert turns[1]["result"] == rows, "the conversation itself is not cut"
	back = room["_whole"](turns, [*sent, {"role": "model", "text": "done"}])
	assert back[1]["result"] == rows and back[-1]["text"] == "done"


def test_a_guide_is_read_without_the_names_of_its_code():
	import re

	room = _lifted(AI / "guide.py", ("CODE", "plain"), {"re": re})
	said = room["plain"]("Release Retention turns it on (`retention._released_ready`). It is paid (when the invoice is).")
	assert said == "Release Retention turns it on. It is paid (when the invoice is)."
	assert "plain(one['text'])" in _source(AI / "guide.py", "how_to")


def test_a_long_guide_section_is_read_to_its_end():
	room = _lifted(AI / "guide.py", ("LONGEST", "parts"), {})
	said = "\n\n".join(f"Paragraph {n} " + "word " * 80 for n in range(12))
	pieces = room["parts"](said)
	assert len(pieces) > 1 and all(len(one) <= room["LONGEST"] for one in pieces)
	assert "Paragraph 11" in pieces[-1], "the end of the section is still there"
