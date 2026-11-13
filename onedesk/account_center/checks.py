"""AccountCenter's part of the integration suite (one_demo/check.py runs it):
AccountCenter as an administrator, and as somebody who isn't."""

import frappe

from onedesk.one_demo.base import as_user
from onedesk.one_demo.check import check


@check
def account_center_opens_each_section_for_whoever_may_see_it():
	"""AccountCenter (account_center/center.py): Layla opens all six sections and
	one person's page from People; Huda, AccountCenter's Manager in the demo,
	opens Plan and Credits and nothing else of the workspace's; Nadia sees
	Yours only, and People, Devices, Plan and Credits and Domains each refuse
	her."""
	from unittest import mock

	from onedesk.account_center import center

	with as_user("wsadmin@one.test"), mock.patch("onedesk.one.account.ask", return_value=[]):
		said = center.sections_of()
		keys = {one["key"] for one in said["sections"]}
		assert keys == {"profile", "personal", "work", "documents", "signin", "people", "devices", "plan", "domains"}, keys
		for key in keys:
			center.load(key)
		people = center.load("people")
		assert people["used"] and any(one["name"] == "nadia@one.test" for one in people["people"]), people["used"]
		page = center.load("people", "nadia@one.test")
		assert page, "Nadia's page in People is empty"
	with as_user("huda@one.test"), mock.patch("onedesk.one.account.ask", return_value=[]):
		keys = {one["key"] for one in center.sections_of()["sections"]}
		assert keys == {"profile", "personal", "work", "documents", "signin", "plan"}, keys
		said = center.load("plan")
		assert not said["admin"] and set(said["closing"]) == {"closing_on", "deleted_on"}, said["closing"]
	with as_user("nadia@one.test"):
		assert {one["group"] for one in center.sections_of()["sections"]} == {"yours"}
		for key in ("people", "devices", "plan", "domains"):
			try:
				center.load(key)
			except frappe.PermissionError:
				continue
			raise AssertionError(f"somebody who doesn't administer the workspace opened {key}")


@check
def write_my_bio_is_an_action_an_administrator_can_turn_off():
	"""Write My Bio (account_center/agent.py): Layla's words come back from OneAI,
	written from what she said and her employee record; turned off in
	AICenter (one_ai/actions.py) it is gone from the boot and refused, and
	only an administrator turns it."""
	from unittest import mock

	from onedesk.account_center import agent
	from onedesk.one_ai import actions

	with as_user("wsadmin@one.test"):
		with mock.patch("onedesk.one_ai.run.once", return_value=" I run the company. ") as asked:
			assert agent.write_bio("I love facades.") == "I run the company."
		told = asked.call_args.args[1]
		assert "I love facades." in told and "Designation" in told, told
		try:
			actions.switch("write_bio", 0)
			assert not actions.for_boot()["write_bio"]
			try:
				agent.write_bio("x")
				raise AssertionError("Write My Bio ran while it was off")
			except frappe.PermissionError:
				pass
		finally:
			actions.switch("write_bio", 1)
		assert actions.on("write_bio")
	with as_user("nadia@one.test"):
		try:
			actions.switch("write_bio", 0)
			raise AssertionError("Nadia turned an action off")
		except frappe.PermissionError:
			pass


@check
def auto_topup_is_an_administrators_and_asks_oneadmin():
	"""Auto Top-Up (account_center/bills.py): an administrator reads and sets it
	through OneAdmin, and somebody who isn't is refused."""
	from unittest import mock

	from onedesk.account_center import bills

	with mock.patch("onedesk.one.account.ask", return_value={"enabled": 1}) as asked:
		with as_user("wsadmin@one.test"):
			assert bills.auto_topup() == {"enabled": 1}
			assert bills.set_auto_topup(1, "pack", 100, 1) == {"enabled": 1}
		assert asked.call_args.kwargs == {"enabled": 1, "pack": "pack", "below": 100, "cap": 1}
		with as_user("nadia@one.test"):
			try:
				bills.set_auto_topup(1, "pack", 100, 1)
				raise AssertionError("Auto Top-Up was set by somebody who may not")
			except frappe.PermissionError:
				pass
