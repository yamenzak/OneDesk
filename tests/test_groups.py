"""OneAI's tool groups (one_ai/groups.py): every tool is in one, and a
request is given the right ones."""

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

GROUPS = tree.APP / "one_ai" / "groups.py"
TOOLS = tree.APP / "one_ai" / "tools.py"
HOOKS = (tree.APP / "hooks.py").read_text(encoding="utf-8")


def _lifted() -> dict:
	"""CORE, GROUPS and the pure functions, without importing frappe."""
	body = ast.parse(GROUPS.read_text(encoding="utf-8"))
	wanted = [
		n
		for n in body.body
		if (isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") in ("CORE", "GROUPS"))
		or (isinstance(n, ast.FunctionDef) and n.name in ("of", "worded", "used"))
	]
	room: dict = {"re": re}
	exec(compile(ast.Module(body=wanted, type_ignores=[]), str(GROUPS), "exec"), room)
	return room


def _hooked() -> set[str]:
	listed = set()
	for hook in ("one_ai_reads", "one_ai_suggests"):
		block = HOOKS.split(f"{hook} = [", 1)[1].split("\n]", 1)[0]
		listed |= {path.rsplit(".", 1)[1] for path in re.findall(r'"(onedesk\.[\w.]+)"', block)}
	return listed


def test_every_tool_is_in_one_group_or_the_core():
	room = _lifted()
	core, groups = set(room["CORE"]), room["GROUPS"]
	grouped = [tool for group in groups.values() for tool in group["tools"]]
	assert len(grouped) == len(set(grouped)), "a tool is in two groups"
	assert not core & set(grouped), "a core tool is also in a group"
	missing = _hooked() - core - set(grouped)
	assert not missing, f"in no group, so never given to a request: {sorted(missing)}"
	unknown = (core | set(grouped)) - _hooked() - {
		"list_records", "read_record", "count_records", "describe_type", "find_records", "search_everywhere",
		"about_field", "what_links_here", "what_can_happen", "run_report", "about_record", "recall",
		"search_my_chats", "how_to", "remember", "create_record", "edit_record", "delete_record", "move_record",
		"more_tools",
	}  # fmt: skip
	assert not unknown, f"named in a group but not a tool: {sorted(unknown)}"


def test_every_group_says_what_it_is_for():
	for name, group in _lifted()["GROUPS"].items():
		assert len(group["about"]) > 30, name


def test_words_point_to_groups_in_three_languages():
	worded = _lifted()["worded"]
	assert "mail" in worded("Move any email with the word invoice into a folder")
	assert "mail" in worded("انقل الرسائل إلى مجلد")
	assert "crm" in worded("Lege einen Lead an")
	assert "studio" in worded("Write an extension that stops a save")
	assert worded("Can you order pizza for the office?") == set()


def test_a_conversation_keeps_the_groups_it_used():
	used = _lifted()["used"]
	turns = [
		{
			"role": "model",
			"calls": [{"tool": "suggest_mail_rule"}, {"tool": "my_day"}, {"tool": "list_records"}],
		}
	]
	assert used(turns) == {"mail"}, "the core and `you` are given anyway"


def test_more_tools_is_core_and_widens_the_run():
	tools = TOOLS.read_text(encoding="utf-8")
	assert "def more_tools(" in tools and "	more_tools,\n" in tools
	run = (tree.APP / "one_ai" / "run.py").read_text(encoding="utf-8")
	assert 'want.get("tool") == "more_tools"' in run and "offered = surface.declared(given)" in run
	chat = (tree.APP / "one_ai" / "chat.py").read_text(encoding="utf-8")
	assert "groups=groups.chosen(text, page, turns)" in chat
