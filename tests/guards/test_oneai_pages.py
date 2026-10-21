"""OneAI knows every page it is opened on.

The panel says where the reader is with every question (one_ai/chat.py,
_page). A form or a list says it by itself; a page says only its title unless
a `one_ai_page` hook answers for it, and then "this" means nothing to the
model. So every desk page One ships is named by one of those hooks, and a new
page fails here until its module says what the reader sees on it and which
tools read it.
"""

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "onedesk"


def _hook(name: str):
	for node in ast.parse((APP / "hooks.py").read_text(encoding="utf-8")).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == name:
			return ast.literal_eval(node.value)
	return None


def _answering() -> str:
	"""The source of every module whose `page` the hook names."""
	said = ""
	for path in _hook("one_ai_page"):
		module = path.rsplit(".", 1)[0].split(".", 1)[1].replace(".", "/")
		said += (APP / f"{module}.py").read_text(encoding="utf-8")
	return said


def _pages() -> list[str]:
	return sorted(json.loads(path.read_text())["name"] for path in APP.glob("*/page/*/*.json"))


def test_every_page_is_told_to_oneai():
	said = _answering()
	untold = [name for name in _pages() if f'"{name}"' not in said]
	assert not untold, (
		f"OneAI is told only the title of {untold}: answer for each in its module's ai.page, "
		"and name that function in hooks.one_ai_page"
	)


def test_every_answer_is_a_function_that_exists():
	for path in _hook("one_ai_page"):
		module, function = path.rsplit(".", 1)
		source = (APP / (module.split(".", 1)[1].replace(".", "/") + ".py")).read_text(encoding="utf-8")
		assert f"\ndef {function}(" in source, f"{path} does not exist"


#: Each kind of rail entry, and how `where` in public/js/oneai.js knows it is
#: there: the route it opens and what is sent for it.
WHERE = {
	"DocType": 'kind === "list"',
	"Page": "frappe.pages[route[0]]",
	"URL": "frappe.pages[route[0]]",
	"Report": 'kind === "query-report"',
	"Dashboard": 'kind === "dashboard-view"',
	"Workspace": 'kind === "workspaces"',
}


def test_every_kind_of_rail_entry_is_sent_to_oneai():
	"""The browser says where the reader is for every kind of entry a rail
	has, and one_ai/here.py, which the demo check `oneai_is_told_what_every_place_shows` walks
	every entry with, sends the same for each."""
	kinds = set()
	for path in APP.glob("*/sidebar/*/*.json"):
		kinds |= {one.get("link_type") for one in json.loads(path.read_text())["items"] if one.get("type") == "Link"}
	js = (APP / "public" / "js" / "oneai.js").read_text(encoding="utf-8")
	where = js[js.index("where() {") : js.index("home() {")]
	mirror = (APP / "one_ai" / "here.py").read_text(encoding="utf-8")
	unknown = kinds - WHERE.keys()
	assert not unknown, f"a rail entry of kind {sorted(unknown)}: say in oneai.js `where` what it shows, and in here.sent"
	for kind in kinds:
		assert WHERE[kind] in where, f"oneai.js `where` sends nothing for a {kind} entry"
		assert f'kind == "{kind}"' in mirror, f"one_ai/here.py `sent` does not know a {kind} entry"
