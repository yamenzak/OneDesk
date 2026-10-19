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
	assert 'after_app_install = ["onedesk.one.private.installed_now"]' in HOOKS
	assert 'before_app_uninstall = ["onedesk.one.private.refuse_uninstall"]' in HOOKS
	apps = (tree.APP / "one" / "apps.py").read_text()
	assert 'offered() if not one.get("kept")' in apps, "save refuses to turn a private app off"
	companions = (tree.APP / "one" / "companions.py").read_text()
	assert "(*COMPANIONS, *private.names())" in companions and "| private.rail()" in companions
	proxy = (tree.APP / "one_admin" / "proxy.py").read_text()
	assert "limit=CLAIMS_AN_HOUR" in proxy and "def app_claim(" in proxy
