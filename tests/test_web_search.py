"""Web search (docs/AICENTER.md, Web search): what the account asks
Cloudflare, what comes back, and that the workspace offers the tool only
while its service is on."""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree  # noqa: E402

ADMIN = (tree.APP / "one_admin" / "web.py").read_text()
WORKSPACE = (tree.APP / "one_ai" / "ai_web.py").read_text()
GROUPS = (tree.APP / "one_ai" / "groups.py").read_text()
TOOLS = (tree.APP / "one_ai" / "tools.py").read_text()


def _lifted(source: str, names: tuple) -> dict:
	space = {}
	for node in ast.parse(source).body:
		named = getattr(node.targets[0], "id", "") if isinstance(node, ast.Assign) else getattr(node, "name", "")
		if named in names:
			exec(ast.unparse(node), space)
	return space


def test_only_the_question_is_sent_to_one_provider():
	space = _lifted(ADMIN, ("PROVIDER", "MOST", "LONGEST", "body"))
	asked = space["body"]("  Gulf   Extrusions\nDubai ", 50, "one")
	assert asked == {"query": "Gulf Extrusions Dubai", "provider": "exa", "limit": space["MOST"], "options": {"gateway": {"id": "one"}}}
	assert len(space["body"]("x" * 5000, 3, "one")["query"]) == space["LONGEST"]
	assert space["body"]("a", 0, "one")["limit"] == 5


def test_pages_are_an_address_a_title_and_what_it_says():
	space = _lifted(ADMIN, ("found",))
	answer = {"items": [{"url": "https://gulf.example", "title": "Gulf", "description": "Aluminium"}, {"title": "no address"}]}
	assert space["found"](answer) == [{"url": "https://gulf.example", "title": "Gulf", "about": "Aluminium"}]
	assert space["found"]({}) == []


def test_the_search_is_billed_and_released_when_it_fails():
	assert "ledger.reserve(" in ADMIN and "ledger.release(holding)" in ADMIN and "ledger.commit(" in ADMIN


def test_the_tool_is_offered_and_run_only_while_the_service_is_on():
	assert 'services.call(SERVICE, account.ask, ASKED' in WORKSPACE, "asked only through services.call"
	assert "web_search.service = SERVICE" in WORKSPACE
	assert "tuple(filter(offered, reads))" in TOOLS, "a tool that needs a service is not given while it is off"
	assert '"service": "web_search"' in GROUPS and "services.on(needs)" in GROUPS, "nor is its group named"
	assert "grouped.offered(one)" in TOOLS, "nor given when asked for by name"
