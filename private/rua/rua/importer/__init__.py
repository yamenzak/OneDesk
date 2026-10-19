"""The old Rua app brought into One, once, and checked.

Each step reads the old records, makes what they become, and remembers the
pair in `Rua Import Record`, so a run that stops can be run again and picks
up where it was. The order matters: parties before projects, projects
before their orders, invoices before the receipts that pay them. The last
step compares the old app's own totals with the books.
"""

import traceback

import frappe
from frappe.utils import now_datetime

STEPS = (
	"parties",
	"projects",
	"quotations",
	"buying",
	"sales",
	"payments",
	"people",
	"attendance",
	"files",
	"numbers",
	"settle",
	"check",
)
SINGLE = "Rua Import"


def run(only=None):
	"""Run every step, or the ones named in `only`, committing after each."""
	from rua import setup
	from rua.importer.base import Run
	from rua.source import Source

	source = Source.configured()
	if not source:
		frappe.throw(
			"This site's config doesn't say where the old Rua app is (rua_source or rua_source_dir)."
		)
	steps = [one for one in STEPS if not only or one in (only if isinstance(only, list | tuple) else [only])]
	_status(
		status="Running",
		source="Copy on disk" if source.folder else "Live site",
		started_on=now_datetime(),
		error=None,
	)
	frappe.flags.mute_emails = True
	frappe.flags.in_rua_import = True
	try:
		setup.run()
		run_ = Run(source)
		for step in steps:
			_status(step=step)
			frappe.get_attr(f"rua.importer.{step}.run")(run_)
			frappe.db.commit()
			_notes(run_, step)
		_status(status="Done", step=None, finished_on=now_datetime())
		return run_.made_now
	except Exception:
		frappe.db.rollback()
		_status(status="Failed", error=traceback.format_exc()[-8000:], finished_on=now_datetime())
		raise
	finally:
		frappe.flags.in_rua_import = False


def _status(**values):
	for key, value in values.items():
		frappe.db.set_single_value(SINGLE, key, value)
	frappe.db.commit()


def _notes(run_, step):
	"""The notes a step left, kept on Rua Import in place of any it left last
	time."""
	doc = frappe.get_single(SINGLE)
	kept = [row for row in doc.notes if row.step != step]
	order = {name: index for index, name in enumerate(STEPS)}
	rows = kept + [frappe._dict(one, step=step) for one in run_.notes]
	rows.sort(key=lambda row: order.get(row.get("step"), len(STEPS)))
	doc.set("notes", [])
	for row in rows:
		doc.append(
			"notes",
			{key: row.get(key) for key in ("kind", "reference_doctype", "reference_name", "note", "step")},
		)
	doc.flags.ignore_permissions = True
	doc.save()
	run_.notes = []
	frappe.db.commit()
