"""AICenter as the agents' office (docs/ARC-AI.md, AICenter; P8.2): a level
an administrator chooses stands over the one its app declares, a month's
credit limit and the switch that turns agents off stop them at the door and
at the Worker's way in, Undo asks who may decide, and every change is an
administrator's. No site needed."""

import ast
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import frappe
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from onedesk.one_ai import office  # noqa: E402
from onedesk.one_ai.agents import connect, door, levels, users, workspace  # noqa: E402
from onedesk.one_ai.reading import act  # noqa: E402

OFFICE = ROOT / "onedesk" / "one_ai" / "office.py"


@pytest.fixture
def store(monkeypatch):
	held = {}
	monkeypatch.setattr(workspace, "_held", lambda key: json.loads(held.get(key, "{}")))
	monkeypatch.setattr(workspace, "_keep", lambda key, value: held.__setitem__(key, json.dumps(value)))
	monkeypatch.setattr(workspace, "month", lambda: "2026-11")
	return held


@pytest.fixture
def thrown(monkeypatch):
	def throw(message, exc=frappe.ValidationError, *args, **kwargs):
		raise exc(message)

	monkeypatch.setattr(frappe, "throw", throw)
	monkeypatch.setattr(workspace, "_", lambda text: text)
	monkeypatch.setattr(frappe, "format", lambda value, df=None: str(value))
	monkeypatch.setattr(users, "full_name", lambda agent: f"{agent.app}'s agent")


def test_a_workspace_s_level_stands_over_the_declared_one(store):
	assert levels.of("one_book", "draft_purchase_invoice") == "Draft"
	workspace.choose("one_book", "draft_purchase_invoice", "Do it")
	assert levels.of("one_book", "draft_purchase_invoice") == "Do it"
	workspace.choose("one_book", "no_such_action", "Do it")
	assert levels.of("one_book", "no_such_action") == "Ask First", "a level chosen for no action counts for nothing"
	workspace.choose("one_book", "draft_purchase_invoice", None)
	assert levels.of("one_book", "draft_purchase_invoice") == "Draft"
	assert "one_book" in workspace.chosen()
	workspace.choose("one_book", "no_such_action", None)
	assert workspace.chosen() == {}, "putting the declared level back leaves nothing kept"


def test_a_level_chosen_that_is_none_of_the_three_is_ask_first(store, monkeypatch):
	monkeypatch.setattr(workspace, "chosen_level", lambda app, action: "Sometimes")
	assert levels.of("one_mail", "linking.file") == "Do it", "a stray choice falls back to the declared level"
	assert levels.actions("one_book") == ("draft_purchase_invoice", "draft_payment_entry", "add_bank_transactions", "ask_for_missing_invoice"), "a tool that is also a planner is one action"
	assert "actions.mark" in levels.actions("one_mail") and "hand_on" in levels.actions("one_mail")


def test_a_month_s_spend_counts_by_agent_and_starts_again_each_month(store, monkeypatch):
	workspace.spend("one_book", 2.5)
	workspace.spend("one_book", 1)
	workspace.spend("one_mail", 0)
	assert workspace.spent() == {"one_book": 3.5}
	monkeypatch.setattr(workspace, "month", lambda: "2026-12")
	assert workspace.spent() == {}
	workspace.set_limit("one_book", 10)
	workspace.set_limit(workspace.ALL, "25")
	assert workspace.limits() == {"one_book": 10.0, "*": 25.0}
	workspace.set_limit("one_book", 0)
	assert workspace.limits() == {"*": 25.0}


def test_the_reason_an_agent_stops():
	assert workspace.refused(True, {}, {}, "one_book") == workspace.OFF
	assert workspace.refused(False, {"one_book": 10}, {"one_book": 10}, "one_book") == workspace.OVER
	assert workspace.refused(False, {"one_book": 10}, {"one_book": 9.9}, "one_book") is None
	assert workspace.refused(False, {"one_book": 10}, {"one_book": 50}, "one_mail") is None, "one agent over stops only that one"
	assert workspace.refused(False, {"*": 15}, {"one_book": 8, "one_mail": 7}, "one_crm") == workspace.ALL_OVER
	assert workspace.refused(False, {}, {"one_book": 1e9}, "one_book") is None, "no limit set is no limit"


def test_an_agent_over_its_limit_is_refused_at_the_door_with_the_reason(store, thrown, monkeypatch):
	monkeypatch.setattr(workspace, "on", lambda: True)
	workspace.set_limit("one_book", 5)
	workspace.spend("one_book", 5)
	with pytest.raises(frappe.PermissionError, match="one_book's agent has used its 5.0 credits for this month."):
		door.act_for("one_book", "draft_purchase_invoice", act.Action("Create", "Purchase Invoice", values={}))
	workspace.set_limit("one_book", 0)
	workspace.set_limit(workspace.ALL, 4)
	with pytest.raises(frappe.PermissionError, match="The agents have used their 4.0 credits for this month."):
		workspace.refuse("one_mail")


def test_agents_turned_off_are_refused_at_the_door_the_way_in_and_the_wake(store, thrown, monkeypatch):
	monkeypatch.setattr(workspace, "on", lambda: False)
	with pytest.raises(frappe.PermissionError, match="Agents are turned off for this workspace."):
		door.act_for("one_mail", "hand_on", act.Action("Comment", "Communication", name="x", values={}))
	monkeypatch.setattr(connect, "config", lambda: {"url": "https://agents.test", "secret": "s", "workspace": "acme"})

	def posted(*args, **kwargs):
		raise AssertionError("a wake went out while agents are off")

	monkeypatch.setattr(connect.requests, "post", posted)
	assert connect.wake("one_mail", "mail", {}) is False
	body = (ROOT / "onedesk" / "one_ai" / "agents" / "api.py").read_text().split("def tool(", 1)[1]
	assert body.index("token.verify(") < body.index("workspace.refuse(agent.app)") < body.index("frappe.set_user(agent.email)")
	door_body = (ROOT / "onedesk" / "one_ai" / "agents" / "door.py").read_text().split("def act_for(", 1)[1]
	assert door_body.index("workspace.refuse(app)") < door_body.index("frappe.new_doc(")


def test_undo_is_refused_to_whoever_neither_asked_nor_administers(monkeypatch):
	from onedesk.one import roles

	row = SimpleNamespace(name="RA-1", on_behalf_of="layla@one.test", level="Done", agent="one-book@agents.one.invalid")
	monkeypatch.setattr(frappe, "get_doc", lambda doctype, name: row)
	monkeypatch.setattr(act, "_", lambda text: text)
	monkeypatch.setattr(roles, "administers", lambda user=None: False)
	taken = []
	monkeypatch.setattr(act, "take_back", lambda one: taken.append(one.name))

	def throw(message, exc=frappe.ValidationError, *args, **kwargs):
		raise exc(message)

	monkeypatch.setattr(frappe, "throw", throw)
	monkeypatch.setattr(frappe, "session", SimpleNamespace(user="nadia@one.test"))
	with pytest.raises(frappe.PermissionError):
		act.undo_one("RA-1")
	assert taken == []
	monkeypatch.setattr(frappe, "session", SimpleNamespace(user="layla@one.test"))
	assert act.undo_one("RA-1") == {"undone": 1, "why": None}
	assert taken == ["RA-1"]


def test_an_agent_s_record_counts_what_people_corrected():
	rows = [
		{"agent_action": "hand_on", "level": "Done", "n": 4},
		{"agent_action": "hand_on", "level": "Undone", "n": 1},
		{"agent_action": "hand_on", "level": "Dismissed", "n": 2},
		{"agent_action": "hand_on", "level": "Proposed", "n": 3},
		{"agent_action": "incoming", "level": "Refused", "n": 1},
	]
	assert office.tallied(rows) == {
		"hand_on": {"done": 5, "corrected": 3, "refused": 0, "waiting": 3},
		"incoming": {"done": 0, "corrected": 0, "refused": 1, "waiting": 0},
	}


def test_the_office_is_an_administrator_s_and_its_changes_are_posts():
	tree = ast.parse(OFFICE.read_text())
	whitelisted = [node for node in tree.body if isinstance(node, ast.FunctionDef) and any("whitelist" in ast.unparse(one) for one in node.decorator_list)]
	assert {one.name for one in whitelisted} == {"team", "agent", "set_level", "set_limit", "set_on"}
	for node in whitelisted:
		said = ast.unparse(node.decorator_list[0])
		assert ("POST" in said) == node.name.startswith("set_"), node.name
		first = ast.unparse(node.body[1] if isinstance(node.body[0], ast.Expr) else node.body[0])
		assert first == "roles.require()", node.name
	from onedesk.one_ai import agent

	assert {"office.set_level", "office.set_limit", "office.set_on"} <= set(agent.NOT_FOR_AI)
	center = (ROOT / "onedesk" / "public" / "js" / "one_ai" / "ai_center.js").read_text()
	assert '"onedesk.one_ai.reading.act.undo_one"' in center
	assert 'group: module ? null : __("Apps")' not in center, "a module's OneAI switches sit with its agent, not in a group of their own"
