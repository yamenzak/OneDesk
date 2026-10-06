"""Where a record leads back to, when its home is a page.

A module says which of its kinds live on its pages (`one_homes` in hooks.py),
and the browser puts those crumbs where frappe's list crumb would be.
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
