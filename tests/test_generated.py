"""docs/ and upstream.json are generated, and stale is a failure."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(script: str, *args: str) -> subprocess.CompletedProcess:
	return subprocess.run(
		[sys.executable, str(ROOT / "scripts" / script), *args],
		capture_output=True,
		text=True,
	)


def test_docs_are_current():
	out = _run("docs.py", "--check")
	assert out.returncode == 0, out.stdout + out.stderr


def test_the_framework_reference_is_current():
	out = _run("reference.py", "--check")
	assert out.returncode == 0, out.stdout + out.stderr


def test_upstream_was_read_recently():
	out = _run("upstream.py", "--check")
	assert out.returncode == 0, out.stdout + out.stderr
