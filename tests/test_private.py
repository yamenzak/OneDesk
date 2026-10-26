"""Private apps: a code typed in any case opens its app, a claimed app is
always on, and nothing can uninstall it. See docs/PRIVATE-APPS.md."""

import ast
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

ADMIN = tree.APP / "one_admin" / "private.py"
HOOKS = (tree.APP / "hooks.py").read_text(encoding="utf-8")


def _load(path, names):
	space = {"hashlib": hashlib}
	for node in ast.parse(path.read_text()).body:
		if isinstance(node, ast.FunctionDef) and node.name in names:
			exec(ast.unparse(node), space)
	return space


def test_a_code_reads_the_same_however_it_is_typed():
	space = _load(ADMIN, {"normal", "hashed", "spaced"})
	assert space["spaced"]("ABCDEFGHJKLM") == "ABCD-EFGH-JKLM"
	assert space["normal"](" abcd-efgh jklm ") == "ABCDEFGHJKLM"
	assert space["hashed"]("abcd efgh-jklm") == space["hashed"]("ABCD-EFGH-JKLM")
	assert space["normal"](None) == ""


def test_a_workspace_sees_three_states():
	state = _load(ADMIN, {"state"})["state"]
	assert state("Installed", "Done") == "Installed"
	assert state("Installing", "Waiting") == "Installing"
	assert state("Installing", "Failed") == "Failed"


def test_the_alphabet_has_nothing_to_misread():
	source = ADMIN.read_text()
	alphabet = source.split('ALPHABET = "')[1].split('"')[0]
	assert not set("01OI") & set(alphabet) and len(set(alphabet)) == len(alphabet)


def test_a_private_app_stays():
	assert 'after_app_install = ["onedesk.one_account.private.installed_now"]' in HOOKS
	assert 'before_app_uninstall = ["onedesk.one_account.private.refuse_uninstall"]' in HOOKS
	apps = (tree.APP / "one" / "apps.py").read_text()
	assert 'offered() if not one.get("kept")' in apps, "save refuses to turn a private app off"
	companions = (tree.APP / "one" / "companions.py").read_text()
	assert "(*COMPANIONS, *private.names())" in companions and "| private.rail()" in companions
	proxy = (tree.APP / "one_admin" / "proxy.py").read_text()
	assert "limit=CLAIMS_AN_HOUR" in proxy and "def app_claim(" in proxy


def test_one_never_reaches_into_a_private_app():
	"""A private app plugs into One through One's hooks; One knows none of
	them. Its code never names one, its tests live in the app, and One's
	translations are not extracted from it (babel_extractors.csv)."""
	import re

	private = tree.ROOT / "private"
	names = sorted(path.name for path in private.iterdir() if (path / path.name / "hooks.py").exists())
	assert names, "no private app to check against"
	said = re.compile(r"\b(?:import|from)\s+(?:" + "|".join(map(re.escape, names)) + r")\b|[\"'](?:" + "|".join(map(re.escape, names)) + r")\.")
	found = [
		str(path.relative_to(tree.ROOT))
		for root in (tree.APP, tree.ROOT / "frontend" / "src", tree.ROOT / "scripts")
		for path in root.rglob("*")
		if path.suffix in (".py", ".js", ".vue", ".ts") and "node_modules" not in path.parts and "dist" not in path.parts
		and said.search(path.read_text(encoding="utf-8", errors="ignore"))
	]
	assert not found, f"One reaches into a private app: {found}"
	assert not [path.name for path in (tree.ROOT / "tests").rglob("test_*.py") if any(name in path.stem for name in names)], "a private app's tests belong in the app"
	assert (tree.ROOT / "babel_extractors.csv").read_text().splitlines()[0] == "private/**,ignore"
