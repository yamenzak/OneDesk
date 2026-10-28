"""The demo workspace, built step by step on a new site: Sahara Glass &
Aluminium, a Dubai contractor that sells, designs, fabricates, installs and
maintains glazing, and runs every part of One to do it.

    bench --site <site> execute onedesk.one_demo.build.load --kwargs "{'password': '…'}"
"""

import json

import frappe

DONE = "one_demo_done"

STEPS = (
	"setup",
	"people",
	"plan",
	"masters",
	"stock",
	"buying",
	"crm",
	"projects",
	"making",
	"quality",
	"selling",
	"service",
	"moving",
	"lots",
	"ordering",
	"assets",
	"books",
	"ledger",
	"hr",
	"career",
	"calendar",
	"announcements",
	"privacy",
	"studio",
	"storage",
	"workbook",
	"document",
	"intake",
	"mail",
	"ai",
)


# A step that lives in its module's folder (docs/READY.md, A module's
# folder), by the name the site already knows it by.
MOVED = {"mail": "onedesk.one_mail.demo", "ai": "onedesk.one_ai.demo"}


def done() -> list[str]:
	return json.loads(frappe.db.get_default(DONE) or "[]")


def _mark(step: str) -> None:
	frappe.db.set_default(DONE, json.dumps([*done(), step]))
	frappe.db.commit()


def load(password: str | None = None, only: str | None = None) -> None:
	"""Build what is not built yet, or only the step named."""
	frappe.flags.mute_emails = True
	frappe.flags.in_demo = True
	frappe.set_user("Administrator")
	for step in STEPS:
		if only and step != only:
			continue
		if step in done() and not only:
			continue
		print(f"demo: {step}")
		module = frappe.get_module(MOVED.get(step, f"onedesk.one_demo.{step}"))
		module.run(password=password)
		frappe.db.commit()
		if step not in done():
			_mark(step)
	_reposted()
	from onedesk.one_demo import history

	history.settle()
	frappe.db.commit()
	print("demo: built")


def _reposted() -> None:
	"""The stock values the back-dated entries changed, worked out now as
	ERPNext's hourly job would. Until then the books cannot be locked."""
	from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import (
		execute_reposting_entry,
		get_repost_item_valuation_entries,
	)

	for row in get_repost_item_valuation_entries():
		execute_reposting_entry(row.name)
		frappe.db.commit()
