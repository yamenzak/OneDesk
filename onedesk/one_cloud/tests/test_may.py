"""Who may open a File (one_cloud/namespace.py `may`)."""

from unittest import mock

import frappe

from onedesk.one_cloud import namespace as ns


def test_a_file_of_a_record_that_is_gone_is_nobodys():
	item = {"attached_to_doctype": "News Item", "attached_to_name": "gone", "is_folder": 0}
	with mock.patch.object(frappe, "session", frappe._dict(user="yousef@one.test"), create=True), mock.patch.object(frappe, "has_permission", side_effect=frappe.DoesNotExistError), mock.patch.object(frappe, "clear_last_message", create=True):
		assert ns.may(item) is False
