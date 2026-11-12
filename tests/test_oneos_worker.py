"""OneOS's Worker, its image and Set Up Cloudflare deploying them
(deploy/oneos/README.md)."""

import ast
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SOURCE = (tree.APP / "one_admin" / "setup.py").read_text()
ONEOS = tree.ROOT / "deploy" / "oneos"
WORKFLOW = tree.ROOT / ".github" / "workflows" / "oneos-image.yml"


def _lifted(names: tuple) -> dict:
	space = {"hashlib": hashlib, "os": os, "Path": Path}
	for node in ast.parse(SOURCE).body:
		named = getattr(node.targets[0], "id", "") if isinstance(node, ast.Assign) else getattr(node, "name", "")
		if named in names:
			exec(ast.unparse(node), space)
	return space


def _method(name: str) -> str:
	for node in ast.walk(ast.parse(SOURCE)):
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return ast.unparse(node)
	raise AssertionError(name)


def test_the_image_tag_is_the_folder_s_tree_id(tmp_path):
	"""Set Up Cloudflare names the image by the id the repository gives the
	image folder, which is what the workflow tags it with."""
	space = _lifted(("tree_hash",))
	(tmp_path / "sub").mkdir()
	(tmp_path / "Dockerfile").write_text("FROM x\n")
	(tmp_path / "sub" / "one").write_bytes(b"")
	(tmp_path / "sub.txt").write_text("a")
	run = shutil.which("git")
	if not run:
		pytest.skip("no git here")
	for args in (["init", "-q"], ["add", "."]):
		subprocess.run([run, *args], cwd=tmp_path, check=True, capture_output=True)
	wanted = subprocess.run([run, "write-tree"], cwd=tmp_path, check=True, capture_output=True, text=True).stdout.strip()
	shutil.rmtree(tmp_path / ".git")
	assert space["tree_hash"](tmp_path) == wanted
	assert "git rev-parse HEAD:deploy/oneos/image" in WORKFLOW.read_text()


def test_wrangler_gets_one_class_one_binding_and_the_image():
	space = _lifted(("COMPATIBILITY_CONTAINERS", "ONEOS_IMAGE", "ONEOS_TYPE", "ONEOS_MOST", "wrangler_config"))
	image = space["ONEOS_IMAGE"].format(account="acc1", tag="abc")
	config = space["wrangler_config"]("one-os-dev", "Session", "OS", image, space["ONEOS_TYPE"], space["ONEOS_MOST"])
	assert config["containers"] == [{"class_name": "Session", "image": "registry.cloudflare.com/acc1/one-os:abc", "instance_type": "standard-1", "max_instances": space["ONEOS_MOST"]}]
	assert config["durable_objects"] == {"bindings": [{"name": "OS", "class_name": "Session"}]}
	assert config["migrations"] == [{"tag": "v1", "new_sqlite_classes": ["Session"]}]


def test_set_up_deploys_oneos_with_its_own_secret_and_keeps_its_address():
	assert "self.oneos," in SOURCE
	oneos = _method("oneos")
	assert "for_env(self.env, ONEOS)" in oneos and "tree_hash(source / 'image')" in oneos
	contained = _method("contained")
	assert "vault.get(f'{field}_secret')" in contained and "self.own(f'{field}_url', found[0], secret=False)" in contained
	assert "held.get(name) == wanted" in contained, "deployed again only when the code or the image changes"
	for one in ("worker.js", "guard.js", "package.json"):
		assert f'"{one}"' in SOURCE and (ONEOS / one).exists()
	assert '"oneos_secret"' in (tree.APP / "one_admin" / "vault.py").read_text()


def test_the_worker_guards_both_ways_in():
	"""The /sessions API wants OneAdmin's secret; the browser path wants a
	signed token, then the cookie it leaves; neither starts a container."""
	js = (ONEOS / "worker.js").read_text()
	assert 'same(request.headers.get("x-one-secret") || "", env.ONE_SECRET)' in js
	assert "admitted(env.ONE_SECRET, found.id, cookie(" in js
	assert 'if (now.status !== "healthy") return page(' in js, "a browser never starts a session"
	assert "requiredPorts = [PAGE, STATE]" in js


@pytest.mark.skipif(not shutil.which("node"), reason="no node here")
def test_the_worker_s_own_tests_pass():
	said = subprocess.run(["node", "--test", "guard.test.mjs"], cwd=ONEOS, capture_output=True, text=True, timeout=60)
	assert said.returncode == 0, said.stdout + said.stderr


def test_the_session_sends_the_file_as_a_form_and_answers_state():
	script = (ONEOS / "image" / "one-session").read_text()
	assert 'name="file"' in script and "STATE_PORT = 3100" in script
	assert '"close_write", "-e", "moved_to"' in script, "LibreOffice saves by renaming a new file over the old"
	docker = (ONEOS / "image" / "Dockerfile").read_text()
	assert "HARDEN_DESKTOP=true" in docker and "xprintidle" in docker and "inotify-tools" in docker
