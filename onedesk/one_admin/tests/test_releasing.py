import re
import subprocess
from types import SimpleNamespace

import frappe
import pytest

from onedesk.one_admin import boxes, faults, releasing, servers
from onedesk.one_admin.doctype.workspace_server.workspace_server import WorkspaceServer

MADE = {
	"user": r"useradd\b",
	"subuids": r"--add-subuids",
	"linger": r"enable-linger",
	"image": r"podman build\b",
	"container": r"podman create\b",
	"unit": r"systemctl --user enable\b",
}
UNMADE = {
	"user": r"userdel\b",
	"subuids": r"sed -i .*/etc/subuid",
	"linger": r"disable-linger",
	"image": r"podman rmi\b",
	"container": r"podman rm\b",
	"unit": r"systemctl --user disable\b",
}
MAKING = r"useradd|adduser|groupadd|--add-sub|enable-linger|podman (build|create|run|pull)|systemctl (--user )?enable"


def _commands(text: str) -> list[str]:
	"""The script's own lines, without the files it writes out (a
	Containerfile's lines run inside the image)."""
	kept, until = [], None
	for line in text.splitlines():
		if until:
			until = None if line == until else until
			continue
		found = re.search(r"<<'(\w+)'", line)
		until = found.group(1) if found else None
		kept.append(line)
	return kept


def _first(lines: list[str], pattern: str) -> int:
	return next(at for at, line in enumerate(lines) if re.search(pattern, line))


def test_release_removes_everything_connect_makes_in_the_reverse_order():
	made = _commands(boxes.CONNECT.read_text())
	unmade = _commands(releasing.SCRIPT.read_text())
	assert {re.search(MAKING, line).group(0) for line in made if re.search(MAKING, line)} == {"useradd", "--add-sub", "enable-linger", "podman build", "podman create", "systemctl --user enable"}, "connect.sh makes something release.sh does not know of"
	order = sorted(MADE, key=lambda part: _first(made, MADE[part]))
	assert order == ["user", "subuids", "linger", "image", "container", "unit"]
	assert sorted(UNMADE, key=lambda part: _first(unmade, UNMADE[part])) == order[::-1]


def test_release_removes_only_a_user_connect_made_and_says_what_went():
	text = releasing.SCRIPT.read_text()
	made = boxes.CONNECT.read_text()
	assert 'NAME=one-copies' in text and 'NAME=one-copies' in made
	assert '-c "One copies"' in made and '!= "One copies"' in text
	assert text.index('!= "One copies"') < text.index("userdel")
	assert text.count("gone ") >= 6 and "releasing.released" in text and "X-One-Agent" in text
	assert "apt-get remove" not in text and "apt-get purge" not in text


def test_the_release_script_parses_and_carries_who_it_is():
	script = releasing.script_for("machine-1", "secret", "https://admin.example.com/")
	assert script.startswith("ONE_SERVER=machine-1\nONE_AGENT=secret\nONE_ADMIN=https://admin.example.com\n")
	assert subprocess.run(["bash", "-n"], input=script, text=True, capture_output=True).returncode == 0


def _row(**values):
	return SimpleNamespace(**{"name": "machine-1", "server": "machine-1", "connected": 1, "status": "Up", "pilot_host": "pilot-machine-1.z", **values})


def test_a_server_is_released_only_when_connected_and_empty():
	assert releasing.why_not(_row(connected=0), []) == "ordered"
	assert releasing.why_not(_row(status="Released"), []) == "released"
	assert releasing.why_not(_row(), ["Acme"]) == "placed"
	assert releasing.why_not(_row(), []) is None
	assert releasing.why_not(_row(status="Releasing"), []) is None, "asked again, a new line"


class _Thrown(Exception):
	pass


class _Db:
	def __init__(self):
		self.set = []

	def set_value(self, doctype, name, values, *args, **kwargs):
		self.set.append((doctype, name, values))


@pytest.fixture
def world(monkeypatch):
	db = _Db()
	monkeypatch.setattr(frappe, "db", db, raising=False)
	monkeypatch.setattr(frappe, "throw", lambda message, *_args, **_kwargs: (_ for _ in ()).throw(_Thrown(message)))
	monkeypatch.setattr(releasing, "_", lambda text: text)
	monkeypatch.setattr(frappe, "_", lambda text: text)
	return db


def test_release_refuses_while_workspaces_are_on_it_and_names_them(world, monkeypatch):
	monkeypatch.setattr(releasing.fleet, "row_of", lambda _server: _row())
	monkeypatch.setattr(releasing, "_placed", lambda _server: ["Acme", "Sahara"])
	with pytest.raises(_Thrown, match="Acme, Sahara"):
		releasing.begin("machine-1")
	assert world.set == []


def test_release_ends_the_sessions_first_and_reads_releasing(world, monkeypatch):
	ended = []
	monkeypatch.setattr(releasing.fleet, "row_of", lambda _server: _row())
	monkeypatch.setattr(releasing, "_placed", lambda _server: [])
	monkeypatch.setattr(releasing, "end_sessions", lambda server: ended.append(server) or 2)
	monkeypatch.setattr(releasing, "command", lambda server: f"line for {server}")
	said = releasing.begin("machine-1")
	assert ended == ["machine-1"] and said == {"server": "machine-1", "command": "line for machine-1", "sessions": 2}
	assert world.set == [("Workspace Server", "machine-1", {"status": "Releasing", "open": 0})]


def test_a_session_loses_its_address_before_it_reads_deleted(world, monkeypatch):
	said = []
	monkeypatch.setattr(frappe, "get_all", lambda *_args, **_kwargs: [frappe._dict(name="S-1", slug="s-1"), frappe._dict(name="S-2", slug=None)], raising=False)
	monkeypatch.setattr(releasing.cloudflare, "forget", lambda slug: said.append(("forget", slug)))
	world.set_value = lambda doctype, name, values, *a, **k: said.append(("set", name, values["status"]))
	assert releasing.end_sessions("machine-1") == 2
	assert said == [("forget", "s-1"), ("set", "S-1", "Deleted"), ("set", "S-2", "Deleted")]


class _Cloudflare:
	tunnels = {"t"}

	def __init__(self, *_args):
		self.forgot = []

	def has_tunnel(self, name, tunnel):
		return tunnel in self.tunnels

	def forget(self, name, tunnel, host, zones):
		self.tunnels.discard(tunnel)
		_said.append(("cloudflare", name, tunnel, host, tuple(zones)))


class _Store:
	def __init__(self):
		self.keys = {"servers/machine-1/1-prepare.json", "servers/machine-1/2-update-agent.json", "servers/machine-2/3-x.json"}

	def list_objects_v2(self, Bucket, Prefix):
		return {"Contents": [{"Key": one} for one in sorted(self.keys) if one.startswith(Prefix)]}

	def delete_object(self, Bucket, Key):
		self.keys.discard(Key)


_said = []


def test_finish_tidies_once_and_running_it_again_changes_nothing(world, monkeypatch):
	_said.clear()
	_Cloudflare.tunnels = {"t"}
	row = _row(status="Releasing")
	kept = {"machine-1": {"tunnel": "t", "agent": "a"}}
	store = _Store()

	def held(server):
		if server not in kept:
			raise faults.Refused("no keys")
		return kept[server]

	def set_value(doctype, name, values, *a, **k):
		row.status = values.get("status", row.status)
		world.set.append((doctype, name, values))

	world.set_value = set_value
	monkeypatch.setattr(releasing.fleet, "row_of", lambda _server: row)
	monkeypatch.setattr(releasing.pilot, "held", held)
	monkeypatch.setattr(releasing.pilot, "forget", lambda server: kept.pop(server))
	monkeypatch.setattr(releasing.boxes, "Cloudflare", _Cloudflare)
	monkeypatch.setattr(servers, "_keys", lambda: {"cloudflare_account": "c", "cloudflare_token": "k", "origin_zone": "z", "assets_bucket": "b"})
	monkeypatch.setattr(servers, "_r2", lambda _keys: store)
	monkeypatch.setattr(releasing, "clear_kept", lambda server: _said.append(("defaults", server)))

	assert releasing.finish("machine-1") == ["cloudflare", "r2", "defaults", "keys"]
	assert _said == [("cloudflare", "one-machine-1", "t", "pilot-machine-1.z", ("z",)), ("defaults", "machine-1")]
	assert store.keys == {"servers/machine-2/3-x.json"}
	assert world.set[-1][2]["status"] == "Released" and world.set[-1][2]["pilot_host"] is None
	assert releasing.finish("machine-1") == [], "a released server is left as it is"

	row.status = "Releasing"
	kept["machine-1"] = {"tunnel": "t", "agent": "a"}
	assert releasing.finish("machine-1") == ["defaults", "keys"], "a step already done is not done twice"


def test_finish_refuses_a_server_that_was_never_released(world, monkeypatch):
	monkeypatch.setattr(releasing.fleet, "row_of", lambda _server: _row())
	with pytest.raises(_Thrown):
		releasing.finish("machine-1")
	assert world.set == []


def test_a_server_is_deleted_only_once_released(world):
	flags = frappe._dict()
	for status in ("Up", "Connecting", "Releasing"):
		with pytest.raises(_Thrown, match="Release machine-1"):
			WorkspaceServer.on_trash(SimpleNamespace(status=status, connected=1, server="machine-1", flags=flags))
	with pytest.raises(_Thrown, match="box we ordered"):
		WorkspaceServer.on_trash(SimpleNamespace(status="Up", connected=0, server="se-1", flags=flags))
	WorkspaceServer.on_trash(SimpleNamespace(status="Released", connected=1, server="machine-1", flags=flags))
	WorkspaceServer.on_trash(SimpleNamespace(status="Up", connected=0, server="se-1", flags=frappe._dict(dropped=True)))


def test_a_released_server_joins_again_as_a_new_connection():
	values = servers.joining({"host": "pilot-machine-1.z", "origin": "origin-machine-1.z"}, "abc")
	assert values["status"] == servers.CONNECTING and values["provider"] == "Other" and values["region"] is None
	assert values["pilot_host"] == "pilot-machine-1.z" and values["connected"] == 1 and values["open"] == 0

