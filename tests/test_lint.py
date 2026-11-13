"""A change-mode run of OneLint (scripts/lint.py) judges only the changed
files where a guard judges each file on its own, and a whole run judges every
file (scripts/tree.py, scoped)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import lint  # noqa: E402
import tree  # noqa: E402

from tests.guards import test_helpers, test_oneguard  # noqa: E402


def test_a_change_mode_run_judges_only_the_changed_files(tmp_path, monkeypatch):
	files = [tmp_path / "changed.py", tmp_path / "kept.py"]
	for one in files:
		one.write_text("X = 1\n")
	monkeypatch.delenv(tree.CHANGED, raising=False)
	assert tree.whole() and tree.scoped(files) == files
	monkeypatch.setenv(tree.CHANGED, str(files[0]))
	assert not tree.whole() and tree.scoped(files) == files[:1]


def test_a_guard_judging_each_file_reads_the_changed_one_alone(monkeypatch):
	company = Path("onedesk/one/company.py")
	monkeypatch.setenv(tree.CHANGED, str(company))
	assert test_helpers._ours() == [ROOT / company]
	monkeypatch.delenv(tree.CHANGED)
	assert len(test_helpers._ours()) > 100


def test_a_guard_following_calls_reads_the_changed_file_and_what_it_imports(monkeypatch):
	monkeypatch.setenv(tree.CHANGED, "onedesk/one_task/timer.py")
	code = test_oneguard.Code.of_app.__func__.__wrapped__(test_oneguard.Code)
	assert "one_task/timer.py" in code.trees and "one_hr/payroll.py" not in code.trees
	imported = test_oneguard._imported("from . import board\nfrom onedesk.one import (\n\troles,\n\tpeople,\n)\nimport onedesk.one_cloud.api\n", "onedesk.one_task")
	assert {"onedesk.one_task.board", "onedesk.one.roles", "onedesk.one.people", "onedesk.one_cloud.api"} <= imported


def test_a_whole_run_is_given_no_changed_files(monkeypatch):
	given = []
	monkeypatch.setenv(tree.CHANGED, "left/over.py")
	monkeypatch.setattr(lint.subprocess, "call", lambda command, cwd, env: given.append(env) or 0)
	lint.pytest(["tests"])
	lint.pytest(["tests"], {tree.CHANGED: "onedesk/one_task/timer.py"})
	assert tree.CHANGED not in given[0] and given[1][tree.CHANGED] == "onedesk/one_task/timer.py"
	assert lint.picked([Path("onedesk/one_task/manifest.py")]) is None and lint.picked([Path("upstream.json")]) is None
