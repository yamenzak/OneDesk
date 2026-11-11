import importlib.util
import subprocess
from pathlib import Path
from unittest import mock

import pytest

from onedesk.one_admin import servers

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("agent", ROOT / "deploy" / "server" / "agent.py")
agent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agent)


def test_a_moved_site_keeps_its_own_keys_and_comes_back_on():
	before = {"encryption_key": "k", "db_name": "d", "maintenance_mode": 1, "pause_scheduler": 1}
	made = agent.arrived({**before, "one_token": "t"}, before)
	assert made == {"encryption_key": "k", "db_name": "d", "one_token": "t"}


def test_a_suspended_site_stays_stopped_after_a_move():
	before = {"maintenance_mode": 1, "pause_scheduler": 1, "db_name": "d"}
	made = agent.arrived({"maintenance_mode": 0, "db_name": "d"}, before, quiet=True)
	assert made == before


def test_a_ready_made_bench_lists_the_apps_it_holds():
	listed = agent.listed_apps({"repository": "o/one", "branch": "main"})
	assert [one["name"] for one in listed] == ["erpnext", "hrms", "onedesk"]
	assert listed[-1] == {"name": "onedesk", "repo": "https://github.com/o/one", "branch": "main"}


def test_a_ready_made_bench_lists_its_private_apps_as_linked_checkouts(tmp_path):
	(tmp_path / agent.PRIVATE / "fleet" / ".git").mkdir(parents=True)
	(tmp_path / agent.PRIVATE / "half").mkdir()
	linked = agent.private_apps(tmp_path)
	assert [path.name for path in linked] == ["fleet"], "only a copy the build made a repository of"
	listed = agent.listed_apps({"repository": "o/one", "branch": "main"}, linked)
	assert listed[-1] == {"name": "fleet", "path": str(tmp_path / agent.PRIVATE / "fleet")}
	assert agent.private_apps(tmp_path / "none") == []


def test_a_site_moves_only_to_a_bench_holding_every_app_it_has():
	said = 'Loading...\n{\n "s.one": [\n  "frappe",\n  "onedesk",\n  "fleet"\n ]\n}\n'
	assert agent.unheld(said, "frappe\nerpnext\nonedesk\n") == ["fleet"]
	assert agent.unheld(said, "frappe\nonedesk\nfleet\n") == []
	assert agent.unheld("no listing", "frappe\n") == []


def test_every_instruction_the_admin_sends_is_one_the_agent_knows():
	assert {"prepare", "spare", "move", "drop-bench", agent.UPDATE} <= set(agent.KINDS)


def test_an_instruction_is_only_believed_when_signed():
	assert agent.signature("s", "body") == agent.signature("s", "body") != agent.signature("other", "body")


GOOD = "KINDS = {'update-agent': 1}\ndef main(): pass\n"


def _updating(tmp_path, monkeypatch, source):
	current = tmp_path / "one-agent.py"
	current.write_text("old\n")
	current.chmod(0o755)
	monkeypatch.setattr(agent, "SELF", current)
	agent.update_agent({}, {"source": source})
	return current


def test_a_new_agent_replaces_this_one_and_stays_executable(tmp_path, monkeypatch):
	current = _updating(tmp_path, monkeypatch, GOOD)
	assert current.read_text() == GOOD and current.stat().st_mode & 0o100
	assert sorted(one.name for one in tmp_path.iterdir()) == ["one-agent.py"]


@pytest.mark.parametrize("source", ["def broken(:\n", "raise SystemExit(1)\n", "KINDS = {}\ndef main(): pass\n"])
def test_an_agent_that_does_not_load_or_cannot_update_is_refused(tmp_path, monkeypatch, source):
	with pytest.raises(subprocess.CalledProcessError):
		_updating(tmp_path, monkeypatch, source)
	assert (tmp_path / "one-agent.py").read_text() == "old\n"
	assert sorted(one.name for one in tmp_path.iterdir()) == ["one-agent.py"]


def test_what_is_reported_does_not_carry_the_agent_back():
	said = agent.told({"id": "1", "kind": agent.UPDATE, "source": "x"}, ok=True)
	assert said == {"id": "1", "kind": agent.UPDATE, "ok": True}


def test_a_box_updates_its_agent_before_it_builds():
	keys = {"origin_zone": "z", "cloudflare_account": "a", "cloudflare_token": "t"}
	about = {"frappe": "f", "erpnext": "e", "hrms": "h"}
	row = mock.MagicMock(server="eu-1", pilot_host="p", origin_host="o", benches=None)
	with (
		mock.patch.object(servers, "_keys", return_value=keys),
		mock.patch.object(servers.boxes, "release_of", return_value=about),
		mock.patch.object(servers.boxes, "agent_of", return_value="source"),
		mock.patch.object(servers.boxes, "Cloudflare"),
		mock.patch.object(servers.pilot, "held", return_value={"tunnel": "t"}),
		mock.patch.object(servers.tell, "operators", return_value=[]),
		mock.patch.object(servers, "_own_address", return_value=[]),
		mock.patch.object(servers, "_save"),
		mock.patch.object(servers.frappe, "get_cached_value", return_value="d"),
		mock.patch.object(servers.frappe.utils, "now_datetime", return_value="2026-11-11 10:00:00"),
		mock.patch.object(servers, "instruct") as instruct,
	):
		servers.prepare(row, "abcdef012345")
	assert [one.args[1] for one in instruct.call_args_list] == [servers.AGENT_UPDATE, "prepare"]
	assert instruct.call_args_list[0].kwargs == {"source": "source"}
	assert servers.AGENT_UPDATE == agent.UPDATE
