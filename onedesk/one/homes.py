"""Where a record leads back to, when its home is a page.

frappe's form trail is the record's list, then the record. A kind of record
One keeps on a page of its own (a department on Masters) has a list nobody
reaches: no rail links it. So its trail named a list the reader never came
from, and left out the page they did.

A module says which of its kinds live on its pages (`one_homes` in hooks.py),
as {doctype: [{label, route}, ...]}, for the person reading; the browser puts
those crumbs where frappe's list crumb would be (public/js/shell.js). A kind
the rail links keeps frappe's own crumb.
"""

import frappe


def for_boot() -> dict[str, list[dict]]:
	"""Every module's homes for this person, the first module's word kept."""
	found: dict[str, list[dict]] = {}
	for path in frappe.get_hooks("one_homes"):
		try:
			said = frappe.get_attr(path)() or {}
		except frappe.PermissionError:
			continue
		for doctype, crumbs in said.items():
			found.setdefault(doctype, [{"label": str(one["label"]), "route": one["route"]} for one in crumbs])
	return found
