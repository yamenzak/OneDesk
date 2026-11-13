"""The integration suite: the demo workspace read back as the people in it.

    bench --site <site> execute onedesk.one_demo.check.run
    bench --site <site> execute onedesk.one_demo.check.run --kwargs "{'only': 'oneproject_'}"

`only` names one check, or ends in "_" to run a group: every check whose name
starts with it, such as a module's.
"""

import traceback
from contextlib import contextmanager

import frappe
from frappe.utils import now_datetime

from onedesk.one_demo.checking import CHECKS, _unasked


def run(only: str | None = None) -> int:
	from onedesk.one import dev
	from onedesk.one_demo.samples import unkept

	dev.require()
	failed = []
	chosen = [fn for fn in CHECKS if not only or fn.__name__ == only or (only.endswith("_") and fn.__name__.startswith(only))]
	with _unsent():
		with _on_disk():
			_each(chosen, failed, unkept)
	print(f"{len(chosen) - len(failed)} of {len(chosen)} passed" if len(chosen) != 1 else "")
	return len(failed)


@contextmanager
def _on_disk():
	"""Files the checks make stay on this machine, as on a workspace with no
	store, so a run sends nothing to R2 and reads back what it wrote. A check
	of the store switches it on for itself."""
	was = frappe.conf.get("onestorage_on_disk")
	frappe.conf.onestorage_on_disk = 1
	try:
		yield
	finally:
		frappe.conf.onestorage_on_disk = was


@contextmanager
def _unsent():
	"""No mail leaves while the checks run, and none they made is kept: a
	check that commits (a notification, a screen gone quiet) escapes the
	rollback, and each run once left a few hundred in the queue. frappe's
	suspend_email_queue holds the worker; what was queued since is dropped."""
	held = frappe.db.get_default("suspend_email_queue")
	frappe.db.set_default("suspend_email_queue", 1)
	frappe.db.commit()
	started = now_datetime()
	try:
		yield
	finally:
		made = frappe.get_all("Email Queue", filters={"creation": [">=", started]}, pluck="name")
		for at in range(0, len(made), 500):
			frappe.db.delete("Email Queue Recipient", {"parent": ["in", made[at : at + 500]]})
			frappe.db.delete("Email Queue", {"name": ["in", made[at : at + 500]]})
		frappe.db.set_default("suspend_email_queue", held or 0)
		frappe.db.commit()


def _each(chosen, failed, unkept) -> None:
	for fn in chosen:
		flags = frappe._dict(frappe.flags)
		try:
			with unkept():
				fn()
			print(f"ok    {fn.__name__}")
		except Exception as e:
			failed.append(fn.__name__)
			here = [
				f"{one.filename.rsplit('/', 1)[-1]}:{one.lineno}"
				for one in traceback.extract_tb(e.__traceback__)
				if one.filename.endswith(("/checks.py", "/checking.py"))
			]
			last = traceback.extract_tb(e.__traceback__)[-1]
			said = str(e) or f"line {last.lineno}: {last.line}"
			print(f"FAIL  {fn.__name__} ({here[-1] if here else '?'}): {type(e).__name__} {said[:600]}")
		finally:
			frappe.db.rollback()
			frappe.clear_cache()
			_unasked()
			frappe.local.response = frappe._dict({"docs": []})
			frappe.set_user("Administrator")
			frappe.local.flags = frappe._dict(flags)
			frappe.local.cache = {}


def _modules() -> None:
	"""The checks, registered by importing them: the demo's own first, then
	each module's, in its folder (docs/READY.md, A module's folder), in the
	registry's order. Every module has a checks.py."""
	import importlib

	from onedesk.one import ready

	for folder in ("one_demo", *(spec["folder"] for spec in ready.MODULES.values())):
		importlib.import_module(f"onedesk.{folder}.checks")


_modules()
