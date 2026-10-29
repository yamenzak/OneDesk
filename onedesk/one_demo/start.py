"""The demo company in one click: the setup wizard's first screen offers it on
a workspace not set up yet, the build runs in the background (build.py), and
the wizard follows it until One opens."""

from typing import Annotated

import frappe
from frappe import _
from frappe.utils.background_jobs import get_job_status

from onedesk.one.roles import ADMINISTRATOR
from onedesk.one_demo import build

JOB = "one_demo_build"
BUILT = "one_demo_built"


def _may() -> None:
	frappe.only_for(ADMINISTRATOR)
	if frappe.is_setup_complete() and "setup" not in build.done():
		frappe.throw(_("The demo company goes only into a workspace that is not set up yet."))


@frappe.whitelist(methods=["POST"])
def start(password: Annotated[str, "Everybody's password in the demo company."]) -> dict:
	"""Build the demo company in the background, unless it is being built."""
	_may()
	if len(password or "") < 8:
		frappe.throw(_("Use at least 8 characters."))
	if get_job_status(JOB) not in ("queued", "started"):
		frappe.enqueue(
			"onedesk.one_demo.start.run", queue="long", timeout=3 * 3600, job_id=JOB, password=password
		)
	return progress()


def run(password: str) -> None:
	frappe.flags.one_demo_lenient = True
	build.load(password=password)
	frappe.db.set_default(BUILT, "1")
	frappe.db.commit()


@frappe.whitelist()
def progress() -> dict:
	"""How far the build has got: the steps done of all, and whether it is
	finished or stopped."""
	frappe.only_for(ADMINISTRATOR)
	status = get_job_status(JOB)
	return {
		"done": len(build.done()),
		"of": len(build.STEPS),
		"built": bool(frappe.db.get_default(BUILT)),
		"failed": status == "failed",
		"running": status in ("queued", "started"),
	}
