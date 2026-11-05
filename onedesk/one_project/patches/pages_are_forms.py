"""A project template opens on its form now, with a head (one_project/heads.py)
and its tasks drawn in it, so OneProject's own page of one is gone."""

import frappe

GONE = ("project-template-view",)


def execute():
	for page in GONE:
		frappe.delete_doc("Page", page, ignore_missing=True, force=True, ignore_permissions=True)
