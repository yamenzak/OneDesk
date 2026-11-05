"""Review stamps in the bottom bar, on a dev site only (developer_mode or
one_dev): Island on a page an island still draws, and Passed on a screen
the final passthrough finished, with its day. A screen is named as frappe
routes to it (`Form/Customer`, `List/Customer`, `onemail`); it is added in
the commit that finishes its pass and taken out by a change that undoes it.
"""

import re

PASSED: dict[str, dict] = {
	# "Form/Customer": {"on": "2026-11-02", "pass": "Final passthrough"},
	"Form/Stock Entry": {"on": "2026-11-05", "pass": "OneInventory, stock"},
	"List/Batch": {"on": "2026-11-05", "pass": "OneInventory, stock"},
	"Form/Batch": {"on": "2026-11-05", "pass": "OneInventory, stock"},
}

SCREEN = re.compile(r"^((Form|List|Tree|Report|query-report|print)/[^/]+|[a-z0-9-]+)$")


def dev() -> bool:
	from onedesk.one import dev

	return dev.site()


def for_boot() -> dict:
	"""What the stamps need, on a dev site; nothing anywhere else."""
	if not dev():
		return {}
	return {"dev": 1, "passed": PASSED}
