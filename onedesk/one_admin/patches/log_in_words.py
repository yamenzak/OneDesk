"""The log's rows before `one_admin/log.py`, in its words: the code's own
phrases ("the clock") as the fixed phrases the list translates, a plan's and
an add-on's key as their names, and who did it from who wrote the row."""

import re

import frappe

from onedesk.one_admin import log, site

WAS = {
	"a payment failed": "owed",
	"paid": "paid",
	"the clock": "clock",
	"press has stopped serving the site": "stopped",
	"the site is gone; the files are not": "archived",
	"the files are gone": "dropped",
}


def _label(key: str) -> str:
	return frappe.db.get_value("Offering", key.strip(), "label") or key.strip()


def execute():
	if not frappe.db.exists("DocType", "Tenant Event"):
		return
	for one in frappe.get_all("Tenant Event", fields=["name", "kind", "detail", "owner"]):
		detail = one.detail or ""
		if detail in WAS:
			detail = log.said(WAS[detail])
		elif one.kind in ("Plan Changed", "Add-on Changed") and not detail.startswith(("press", "database")):
			plan, _, rest = detail.partition(" with ")
			extras = [re.match(r"(\d+) × (.+)", part.strip()) for part in rest.split(",")] if rest else []
			detail = " + ".join(
				[_label(plan), *(f"{m.group(1)} × {_label(m.group(2))}" for m in extras if m)]
			)
		if one.owner == "Guest" and one.kind in ("Plan Changed", "Add-on Changed"):
			by = "Customer"
		elif one.owner not in ("Guest", "Administrator") and site.OPERATOR in frappe.get_roles(one.owner):
			by = "Operator"
		else:
			by = "One"
		# An operator's fall was written as "the clock" by the code before.
		if by == "Operator" and (one.detail or "") == "the clock":
			detail = log.said("by_hand")
		frappe.db.set_value(
			"Tenant Event",
			one.name,
			{"detail": detail, "by": by, "by_user": one.owner if by == "Operator" else None},
			update_modified=False,
		)
