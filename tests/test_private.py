"""Private apps: a code typed in any case opens its app, a claimed app is
always on, and nothing can uninstall it. See docs/PRIVATE-APPS.md."""

import ast
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

ADMIN = tree.APP / "one_admin" / "private.py"
HOOKS = tree.hooks()


def _load(path, names):
	space = {"sha256_hash": lambda text: hashlib.sha256(text.encode()).hexdigest()}
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


def test_a_release_adds_and_updates_its_private_apps_and_keeps_a_claimed_one():
	planned = _load(ADMIN, {"planned"})["planned"]
	held = {
		"fleet": {"title": "Fleet", "said": "Vans.", "icon": "truck", "grants": 0},
		"kept": {"title": "Kept", "said": "", "icon": "", "grants": 1},
		"gone": {"title": "Gone", "said": "", "icon": "", "grants": 0},
	}
	declared = [
		{"app": "fleet", "title": "Fleet", "said": "Vans and drivers.", "icon": "truck"},
		{"app": "routes", "title": "Routes"},
		{"app": "Bad-Name", "title": "Bad"},
		"not a dict",
	]
	plan = planned(declared, held)
	assert plan["add"] == {"routes": {"title": "Routes", "said": "", "icon": ""}}
	assert plan["change"] == {"fleet": {"title": "Fleet", "said": "Vans and drivers.", "icon": "truck"}}
	assert plan["drop"] == ["gone"], "a record a workspace holds a code for stays"
	assert planned([{"app": "fleet", "title": "Fleet", "said": "Vans.", "icon": "truck"}], held) == {"add": {}, "change": {}, "drop": ["gone"]}
	assert planned([], {}) == {"add": {}, "change": {}, "drop": []}


def _placing():
	import importlib.util

	spec = importlib.util.spec_from_file_location("placing", tree.ROOT / "deploy" / "release" / "private.py")
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


def test_every_private_app_here_can_join_the_bench():
	"""Its Python package and Frappe modules are its own, against One's and
	against frappe's, erpnext's and hrms's where they sit beside it: a
	module name is bench-wide (frappe.local.module_app), and every release
	bench carries every private app."""
	placing = _placing()
	held = {placing.scrub(line) for line in (tree.APP / "modules.txt").read_text().splitlines() if line.strip()}
	for name in ("frappe", "erpnext", "hrms"):
		held |= placing.modules(tree.ROOT.parent / name)
	assert placing.checked(placing.found(tree.ROOT), {"frappe", "erpnext", "hrms", "onedesk"}, held) == []


def _app(root, name, hooks='one_private_app = {"title": "T"}\n', modules="Fleet", project=None):
	package = root / "private" / name / name
	package.mkdir(parents=True)
	if hooks is not None:
		(package / "hooks.py").write_text(hooks)
	(package / "modules.txt").write_text(modules + "\n")
	(package.parent / "pyproject.toml").write_text(f'[project]\nname = "{project or name}"\n')


def test_a_private_app_that_would_break_the_bench_is_refused(tmp_path):
	placing = _placing()
	_app(tmp_path, "fleet", modules="Fleet\nOne CRM")
	_app(tmp_path, "accounts", modules="Accounts")
	_app(tmp_path, "plain", hooks='app_name = "plain"\n', modules="Plain")
	_app(tmp_path, "renamed", modules="Renamed", project="other")
	_app(tmp_path, "twin", modules="Fleet")
	_app(tmp_path, "loose", hooks=None, modules="Loose")
	_app(tmp_path, "Upper", modules="Upper")
	wrong = placing.checked(placing.found(tmp_path), {"frappe", "onedesk", "accounts"}, {"accounts", "one_crm"})
	said = "\n".join(wrong)
	assert "private/Upper:" in said
	assert "private/accounts: accounts is already a Python package" in said
	assert "private/accounts: its modules accounts are already another app's" in said
	assert "private/fleet: its modules one_crm" in said
	assert "private/twin: its modules fleet" in said, "two private apps clash with each other too"
	assert "private/plain: its hooks.py has no one_private_app" in said
	assert "private/renamed: its pyproject.toml must name the project renamed, not other" in said
	assert "private/loose is not a Frappe app" in said
	assert len(wrong) == 8
	assert placing.checked(placing.found(tmp_path / "nothing"), set(), set()) == []


def test_the_build_names_no_private_app_and_keeps_them_off_the_template():
	import re

	names = [path.name for path in (tree.ROOT / "private").iterdir() if (path / path.name / "hooks.py").exists()]
	built = [path for root in (tree.ROOT / "deploy", tree.ROOT / ".github") for path in root.rglob("*") if path.is_file()]
	assert not [str(path) for path in built for name in names if re.search(rf"\b{re.escape(name)}\b", path.read_text(errors="ignore"))]
	build = (tree.ROOT / "deploy" / "release" / "build.sh").read_text()
	assert 'in_pilot "$repo/deploy/release/private.py" "$bench" "$repo"' in build
	assert "--apps frappe erpnext hrms onedesk " in build, "the template site carries no private app"
	assert "if private.names():" in (tree.APP / "one_admin" / "spares.py").read_text()
	boot = (tree.ROOT / "deploy" / "server" / "first-boot.sh").read_text()
	agent = (tree.ROOT / "deploy" / "server" / "agent.py").read_text()
	assert "deploy/release/private.py" in boot and '/ "private.py"' in agent
	assert f'PRIVATE = "{_placing().HELD}"' in agent, "the agent looks where the build puts them"
