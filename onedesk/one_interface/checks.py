"""OneInterface's part of the integration suite (one_demo/check.py runs it):
the review stamps reach the desk only on a dev site, and every screen named
as passed is one frappe can route to."""

from unittest.mock import patch

import frappe

from onedesk.one_demo.checking import check


@check
def stamps_reach_only_a_dev_site():
	"""The boot carries the stamps on a site in developer mode or marked
	one_dev, and nothing at all anywhere else (one_interface/stamps.py)."""
	from onedesk.one_interface import stamps

	with patch.dict(frappe.conf, {"developer_mode": 0, "one_dev": 0}):
		assert stamps.for_boot() == {}
	with patch.dict(frappe.conf, {"developer_mode": 0, "one_dev": 1}):
		said = stamps.for_boot()
		assert said["dev"] == 1 and said["passed"] is stamps.PASSED
	for screen in stamps.PASSED:
		kind, _, name = screen.partition("/")
		if kind in ("Form", "List", "Tree"):
			assert frappe.db.exists("DocType", name), screen
