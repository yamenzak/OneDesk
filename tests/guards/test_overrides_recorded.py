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
		for method in replaced_in(path.read_text()):
			found.setdefault(method, path.name)
	return found


def replaced_in(source: str) -> list[str]:
	"""The frappe methods a script replaces on a prototype. Pure."""
	return [method for owner, method in REPLACED.findall(source) if not method.startswith(("one_", "__one_")) and not owner.startswith("onedesk.")]


def unrecorded(replaced: dict[str, str], ledger: str) -> list[str]:
	return [f"{method} ({file})" for method, file in replaced.items() if method not in ledger]


def test_every_frappe_method_we_replace_is_recorded():
	missing = unrecorded(replaced(), (ROOT / "scripts" / "overrides.py").read_text())
	assert not missing, "Add a row to scripts/overrides.py for:\n" + "\n".join(missing)


def test_the_recording_rule_catches_its_example():
	source = (
		"frappe.ui.form.Form.prototype.refresh = function () {};\n"
		"frappe.ui.Page.prototype.one_dressed = true;\n"
		"frappe.ui.Page.prototype.__one_wrap = function () {};\n"
		"onedesk.Board.prototype.draw = function () {};\n"
	)
	assert replaced_in(source) == ["refresh"]
	assert unrecorded({"refresh": "form.js"}, 'Row("frappe.ui.form.Form.prototype.setup")') == ["refresh (form.js)"]
	assert unrecorded({"refresh": "form.js"}, 'Row("Form.prototype.refresh")') == []
