"""Point 9: a frappe method we replace in the desk's code is recorded in
scripts/overrides.py, so an upstream change to it breaks a test and not a
screen. A flag we set on a class to wrap it once (`one_*`, `__one_*`) is not a
method, and a method of one of our own classes (`onedesk.…`) replaces nothing."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JS = ROOT / "onedesk" / "public" / "js"
REPLACED = re.compile(r"([\w.]+)\.prototype\.(\w+)\s*=\s*(?:async\s+)?(?:function|\()")


def replaced() -> dict[str, str]:
	"""{method: the first file that replaces it}."""
	found = {}
	for path in sorted(JS.rglob("*.js")):
		for owner, method in REPLACED.findall(path.read_text()):
			if not method.startswith(("one_", "__one_")) and not owner.startswith("onedesk."):
				found.setdefault(method, path.name)
	return found


def test_every_frappe_method_we_replace_is_recorded():
	ledger = (ROOT / "scripts" / "overrides.py").read_text()
	missing = [f"{method} ({file})" for method, file in replaced().items() if method not in ledger]
	assert not missing, "Add a row to scripts/overrides.py for:\n" + "\n".join(missing)
