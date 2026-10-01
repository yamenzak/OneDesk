"""OneAI's setup cards (one/ai_setup.py): a saved report, a dashboard, a report
by mail, a level, a profile, a group and what a person sees, each written as a
card that does nothing until a person approves it, and made then by the page's
own code as that person. These read the code that says so."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SOURCE = (tree.APP / "one" / "ai_setup.py").read_text()
HOOKS = (tree.APP / "hooks.py").read_text()
PROPOSALS = (tree.APP / "one_ai" / "proposals.py").read_text()
TOOLS = (
	"suggest_saved_report",
	"suggest_dashboard",
	"suggest_report_mail",
	"suggest_level",
	"suggest_profile",
	"suggest_group",
	"suggest_hold",
)


def _body(name: str) -> str:
	return SOURCE.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]


def test_every_tool_is_offered_on_the_stronger_model():
	for tool in TOOLS:
		assert f'"onedesk.one.ai_setup.{tool}"' in HOOKS, tool
		assert f"\t{tool},\n" in SOURCE.split("for _tool in (", 1)[1], tool
	assert '_tool.action = "workspace_setup"' in SOURCE
	actions = json.loads((tree.APP / "fixtures" / "ai_action.json").read_text())
	said = next(one for one in actions if one["name"] == "workspace_setup")["instruction"]
	assert "workspace_access" in said and "describe_type" in said


def test_a_card_changes_nothing_until_approved():
	for tool in TOOLS:
		body = _body(tool)
		assert "_card(" in body, tool
		assert ".insert(" not in body and ".save(" not in body, tool
	assert 'proposals.propose("Setup"' in _body("_card")
	assert '"Setup"' in PROPOSALS.split("OWN_WORDS = ", 1)[1].split("\n", 1)[0]


def test_approving_runs_the_pages_own_code():
	apply = _body("apply")
	for call in (
		"save_report(",
		"reports.place(",
		"access.new_level(",
		"access.save_level(",
		"access.save_profile(",
		"access.save_group(",
		"access.hold(",
		"access.let_go(",
	):
		assert call in apply, call
	assert "ai_setup.apply(changes)" in PROPOSALS


def test_what_only_an_administrator_does_is_refused_to_anybody_else():
	for tool in TOOLS[1:]:
		assert "if not roles.administers():" in _body(tool), tool
	assert "everybody and not roles.administers()" in _body("_place")
	assert "roles.require()" in _body("apply")


def test_a_report_or_chart_is_of_a_kind_the_reader_may_read():
	kind = _body("_kind")
	assert 'frappe.has_permission(doctype, "read")' in kind
	assert "meta.module in REFUSED_MODULES" in kind
	assert "df.permlevel" in _body("_field")


def test_a_level_card_says_only_what_changes_and_goes_stale():
	level = _body("suggest_level")
	assert "if r not in have.get(" in level and "if r in have.get(" in level
	assert "nothing would change" in level
	apply = _body("apply")
	assert '_state(access.level(key)["rows"]) != changes["state"]' in apply
	assert "no longer applies" in apply
	assert 'entry.db_set("state", "Stale")' in PROPOSALS


def test_a_report_by_mail_runs_as_whoever_approved_it():
	assert '"user": frappe.session.user' in _body("apply")
