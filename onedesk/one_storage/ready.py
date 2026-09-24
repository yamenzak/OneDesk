"""Whether files are going where they should, and moving the ones that are not.

The **Storage Check** (report/storage_check), drawn by the same page as the
Books and Inventory Checks (public/js/check.js).
"""

import frappe
from frappe import _

from onedesk.one_storage import store

FIXERS = ("Workspace Administrator",)

READY, TO_DO, SUGGESTED = "Ready", "To Do", "Suggested"


def _row(key, check, state, says, fix=None) -> dict:
	return {"key": key, "check": check, "state": state, "says": says, "fix": fix if state != READY else None}


def checks() -> list[dict]:
	return [_linked(), _answers(), _disk()]


def _linked() -> dict:
	check = _("New files go to cloud storage")
	if store.enabled():
		return _row("linked", check, READY, _("Every file uploaded anywhere in One is kept in cloud storage."))
	return _row("linked", check, TO_DO, _("This workspace is not linked to an account, so files are kept on the server's disk."))


def _answers() -> dict:
	check = _("Cloud storage answers")
	if not store.enabled():
		return _row("answers", check, TO_DO, _("Nothing to ask until the workspace is linked to an account."))
	try:
		store.put("files/check/ping.txt", b"ping")
		store.get("files/check/ping.txt")
	except Exception as error:
		return _row("answers", check, TO_DO, _("Storing and reading back a test file failed: {0}").format(str(error)[:140]))
	return _row("answers", check, READY, _("A test file was stored and read back."))


def _disk() -> dict:
	check = _("No file is left on the server's disk")
	waiting = len(store.on_disk())
	if not waiting:
		return _row("disk", check, READY, _("Every file is in cloud storage."))
	if not store.enabled():
		return _row("disk", check, READY, _("{0} files are on the disk, which is where this workspace keeps them.").format(waiting))
	return _row("disk", check, SUGGESTED, _("{0} files from before cloud storage are still on the server's disk.").format(waiting), "move")


@frappe.whitelist(methods=["POST"])
def fix(key: str, **values) -> None:
	frappe.only_for(FIXERS)
	if key == "move":
		frappe.enqueue("onedesk.one_storage.store.move", queue="long", timeout=3600, limit=5000, job_id="onestorage-move", deduplicate=True)
		frappe.msgprint(_("Moving them now. This page says how many are left when you open it again."), alert=True)
	else:
		frappe.throw(_("Nothing to fix for {0}.").format(key))
