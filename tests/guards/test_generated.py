"""docs/, the framework reference and the icon fixtures are generated; stale is a failure."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run(script: str, *args: str) -> subprocess.CompletedProcess:
	return subprocess.run(
		[sys.executable, str(ROOT / "scripts" / script), *args],
		capture_output=True,
		text=True,
	)


def test_docs_are_current():
	"""Read in this process, so the atlas and the parsed code are shared with
	the guards beside it."""
	sys.path.insert(0, str(ROOT / "scripts"))
	import docs

	found = docs.stale()
	assert not found, f"stale: {', '.join(found)}. Run `python scripts/docs.py`."


def test_the_framework_reference_is_current():
	out = _run("reference.py", "--check")
	assert out.returncode == 0, out.stdout + out.stderr


def test_upstream_was_read_recently():
	"""The bench is a reviewed checkpoint (docs/UPSTREAM.md), and a recent one."""
	out = _run("upstream.py", "--check")
	assert out.returncode == 0, out.stdout + out.stderr


def test_the_icon_fixtures_are_current():
	out = _run("icons.py", "--check")
	assert out.returncode == 0, out.stdout + out.stderr


def test_nothing_upstream_moved_under_us():
	out = _run("overrides.py", "--check")
	assert out.returncode == 0, out.stdout + out.stderr


def _script(name: str):
	sys.path.insert(0, str(ROOT / "scripts"))
	import importlib

	return importlib.import_module(name)


def test_the_docs_check_catches_a_stale_page(monkeypatch):
	docs = _script("docs")
	held = ROOT / "upstream.json"
	monkeypatch.setattr(docs, "PAGES", {ROOT / "docs" / "NOWHERE.md": lambda: "x", held: held.read_text})
	assert docs.stale() == ["docs/NOWHERE.md"]


def test_the_reference_and_icon_checks_catch_a_stale_file(monkeypatch, tmp_path):
	reference, icons = _script("reference"), _script("icons")
	monkeypatch.setattr(sys, "argv", ["x", "--check"])
	monkeypatch.setattr(reference, "page", lambda: "stale\n")
	assert reference.main() == 1
	monkeypatch.setattr(reference, "page", (ROOT / "docs" / "FRAMEWORK.md").read_text)
	assert reference.main() == 0
	monkeypatch.setattr(icons, "icons", lambda: [])
	monkeypatch.setattr(icons, "FIXTURE", tmp_path / "custom_icon.json")
	assert icons.main() == 1
	icons.FIXTURE.write_text("[]\n")
	assert icons.main() == 0


def test_the_upstream_check_catches_an_old_checkpoint(monkeypatch):
	upstream = _script("upstream")
	shas = {app: {"sha": f"{app}-sha"} for app in upstream.APPS}
	monkeypatch.setattr(upstream, "head", lambda app, ref="HEAD": f"{app}-sha")
	monkeypatch.setattr(upstream, "problems", lambda text: [])
	monkeypatch.setattr(upstream, "recorded", lambda: {**shas, "note": "upstream.json", "recorded_on": "2026-01-01"})
	assert [one for one in upstream.check() if "days old" in one]
	monkeypatch.setattr(upstream, "recorded", lambda: {**shas, "note": "upstream.json", "recorded_on": upstream.date.today().isoformat()})
	assert upstream.check() == []
	monkeypatch.setattr(upstream, "head", lambda app, ref="HEAD": "moved")
	assert len(upstream.check()) == len(upstream.APPS)


def test_the_overrides_check_catches_a_line_gone(monkeypatch):
	overrides = _script("overrides")
	monkeypatch.setattr(overrides, "OVERRIDES", [("Gone", "why", "onedesk/nowhere.js", "frappe/nowhere.py", "x")])
	monkeypatch.setattr(overrides, "ASKS", {"No row": "ask"})
	assert overrides.missing() == [
		"Gone: our onedesk/nowhere.js is gone",
		"Gone: frappe/nowhere.py is not in the checkout",
		"an ask names no row: No row",
	]
