"""An extension's review now covers where and when it runs as well as its
code (review.fingerprint). One that passed keeps its pass, re-fingerprinted
as it stands; one whose code no longer matches what passed stays unable to
turn on.

Each also gets the name of who asked for it, which the form now shows in
place of their email, and a screen extension's Client Script is made again,
wrapped as a server one's is (guard.wrapped_on_screen)."""

import hashlib

import frappe

from onedesk.one_studio import extensions


def execute():
	for doc in frappe.get_all(
		extensions.EXTENSION, filters={"review": "Passed"}, fields=["name", "code", "reviewed"]
	):
		if doc.reviewed != hashlib.sha256((doc.code or "").encode()).hexdigest():
			continue
		extension = frappe.get_doc(extensions.EXTENSION, doc.name)
		extension.db_set("reviewed", extensions.reviewed_as(extension), update_modified=False)
	for name, user in frappe.get_all(extensions.EXTENSION, fields=["name", "asked_by"], as_list=True):
		if user:
			frappe.db.set_value(
				extensions.EXTENSION,
				name,
				"asked_by_name",
				frappe.db.get_value("User", user, "full_name"),
				update_modified=False,
			)
	for name in frappe.get_all(extensions.EXTENSION, filters={"runs": extensions.ON_SCREEN}, pluck="name"):
		extensions.sync(frappe.get_doc(extensions.EXTENSION, name))
