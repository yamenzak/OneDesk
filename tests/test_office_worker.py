"""The office Worker's checks of a mail's link and attachment, and Set Up
Cloudflare deploying them (deploy/office/README.md)."""

import ast
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SOURCE = (tree.APP / "one_admin" / "setup.py").read_text()
OFFICE = tree.ROOT / "deploy" / "office"


def _lifted(names: tuple) -> dict:
	space = {}
	for node in ast.parse(SOURCE).body:
		named = getattr(node.targets[0], "id", "") if isinstance(node, ast.Assign) else getattr(node, "name", "")
		if named in names:
			exec(ast.unparse(node), space)
	return space


def test_the_office_worker_gets_a_throwaway_browser_and_a_cpu_limit():
	space = _lifted(("COMPATIBILITY_CONTAINERS", "OFFICE_IMAGE", "OFFICE_TYPE", "OFFICE_MOST", "OFFICE_CPU_MS", "wrangler_config", "office_config"))
	config = space["office_config"]("one-office-dev")
	assert config["browser"] == {"binding": "BROWSER"} and "nodejs_compat" in config["compatibility_flags"]
	assert config["limits"] == {"cpu_ms": space["OFFICE_CPU_MS"]}
	assert config["containers"][0]["image"] == space["OFFICE_IMAGE"]
	for one in ("worker.js", "look.js", "package.json"):
		assert (OFFICE / one).exists()
	assert '"look.js"' in SOURCE and '("Browser Rendering*",)' in SOURCE


def test_the_worker_guards_both_checks_with_the_secret():
	js = (OFFICE / "worker.js").read_text()
	assert js.index('request.headers.get("x-one-secret") !== env.ONE_SECRET') < js.index('"/guard/file"')
	assert "puppeteer.launch(env.BROWSER)" in js and "allowed(url)" in js


@pytest.mark.skipif(not shutil.which("node"), reason="no node here")
def test_the_worker_s_own_tests_pass():
	said = subprocess.run(["node", "--test", "look.test.mjs"], cwd=OFFICE, capture_output=True, text=True, timeout=60)
	assert said.returncode == 0, said.stdout + said.stderr
