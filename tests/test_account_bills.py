"""Plan and Credits' invoices (account_center/bills.py)."""

from unittest import mock

import frappe

from onedesk.account_center import bills
from onedesk.one_admin import faults


def test_invoices_say_unreached_rather_than_fail():
	with mock.patch("onedesk.account_center.center._sees_plan", return_value=True), mock.patch("onedesk.one.account.configured", return_value=True), mock.patch("onedesk.one.account.ask", side_effect=faults.Again("down")), mock.patch.object(frappe, "clear_last_message", create=True):
		assert bills.invoices() == {"invoices": [], "linked": True, "reached": False}
