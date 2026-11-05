"""A project and a project template open on their forms now, with a head
(one_project/heads.py) and OneProject's parts drawn in their tabs, so
OneProject's own pages of them are gone."""

import frappe

GONE = ("project-template-view", "project-view")


def execute():
	for page in GONE:
		frappe.delete_doc("Page", page, ignore_missing=True, force=True, ignore_permissions=True)
