"""The release's ready demo: the demo workspace built by build.sh on a copy
of the template site, through the same setup job and builders a demo
session runs (one_demo/build.py), then dumped beside the template as
`<sha>.demo.tar.gz`, which a training copy from the demo restores instead
of building (one_admin/sessions.py, the box's agent `session-ready-demo`).
`name` prints the archive's name, `budget` refuses an archive over its size
budget. Pure but for reading a file's size."""

import sys
from pathlib import Path

SUFFIX = "demo.tar.gz"
BUDGET_MB = 300


def name(sha: str) -> str:
	"""The archive's name beside the template's `<sha>.site.tar.gz`. Pure."""
	return f"{sha}.{SUFFIX}"


def over_budget(size: int, budget_mb: int = BUDGET_MB) -> str | None:
	"""Why an archive of `size` bytes is too big to ship, or None. Pure."""
	if size > budget_mb * 1024 * 1024:
		return f"the ready demo is {size / 1024 / 1024:.0f} MB, over its budget of {budget_mb} MB"
	return None


if __name__ == "__main__":
	command, given = sys.argv[1], sys.argv[2]
	if command == "name":
		print(name(given))
	else:
		why = over_budget(Path(given).stat().st_size)
		if why:
			print(why, file=sys.stderr)
			raise SystemExit(1)
