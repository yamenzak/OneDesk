"""AccountCenter's part of the integration suite (one_demo/check.py runs it):
AccountCenter as an administrator, and as somebody who isn't."""

import frappe

from onedesk.one_demo.base import as_user
from onedesk.one_demo.checking import _asked, _Told, check
from onedesk.one_demo.people import OWNER


@check
def the_payer_downloads_everything_and_closes_the_workspace():
	"""Layla, who pays, prepares the full download and fetches it, closes the
	workspace with her password and keeps it open after all, and everybody,
	she too, is told each. Once somebody else pays she may do none of it, and
	Mariam, who does not administer the workspace, may not even read where
	closing stands. The account is not asked: what it would answer is said
	here."""
	import os
	import zipfile
	from unittest import mock

	from onedesk.account_center import closing

	frappe.db.set_single_value("Workspace Account", "billed_to", OWNER)
	folder = frappe.get_site_path("private", "closing")
	os.makedirs(folder, exist_ok=True)
	with as_user(OWNER), mock.patch("frappe.enqueue") as queued, mock.patch("onedesk.one.account.ask") as asked, mock.patch("onedesk.one.account.refresh"), mock.patch("frappe.utils.password.check_password"):
		assert closing.state()["is_payer"]
		frappe.db.set_single_value("Workspace Account", {"export_status": "", "export_file": ""})
		try:
			closing.download()
			raise AssertionError("a download was sent before one was made")
		except frappe.ValidationError:
			pass
		closing.prepare()
		assert queued.call_args.args[0] == closing.build
		with open(os.path.join(folder, "an-old-one.zip"), "wb") as out:
			out.write(b"PK\x05\x06" + bytes(18))
		with _Told() as told, mock.patch.object(closing, "_database") as database, mock.patch.object(closing, "_files", return_value=[]) as files, mock.patch.object(closing, "_doctypes", return_value=["ToDo", "Project"]), mock.patch.object(closing, "BATCH", 3):
			closing.build(OWNER)
		assert database.called and files.called, "the database and the files go in too"
		held = frappe.get_single("Workspace Account")
		assert held.export_status == "Ready" and os.listdir(folder) == [held.export_file], os.listdir(folder)
		with zipfile.ZipFile(os.path.join(folder, held.export_file)) as zipped:
			rows = zipped.read("records/ToDo.csv").decode("utf-8-sig").strip().splitlines()
			assert len(rows) == frappe.db.count("ToDo") + 1, "a table read three rows at a time came out whole"
		assert told.to("Full Download Ready") == {OWNER}
		_asked(method="GET")
		assert closing.download().status_code == 200
		with _Told() as told:
			closing.close("her password")
			assert asked.call_args.args[0] == "onedesk.one_admin.proxy.close"
			closing.keep()
			assert asked.call_args.args[0] == "onedesk.one_admin.proxy.withdraw_closing"
		for name in ("Workspace Closing", "Workspace Staying Open"):
			assert {OWNER, "mariam@one.test", "rania@one.test"} <= told.to(name), name
		os.remove(os.path.join(folder, held.export_file))
	with as_user(OWNER), mock.patch("onedesk.one.account.ask") as asked:
		try:
			closing.close("not her password")
			raise AssertionError("closed with a wrong password")
		except frappe.ValidationError:
			assert not asked.called
	frappe.db.set_single_value("Workspace Account", "billed_to", "accounts@sahara-parent.example")
	with as_user(OWNER), mock.patch("onedesk.one.account.ask") as asked, mock.patch("frappe.utils.password.check_password"):
		for step in (closing.prepare, closing.download, lambda: closing.close("x"), closing.keep):
			try:
				step()
				raise AssertionError("somebody who does not pay did it")
			except frappe.PermissionError:
				pass
		assert not asked.called and not closing.state()["is_payer"]
	with as_user("mariam@one.test"):
		try:
			closing.state()
			raise AssertionError("Mariam read where closing stands")
		except frappe.PermissionError:
			pass


ACCOUNT = {
	"credit_packs": [{"name": "credits-500", "label": "500 credits", "amount": 25, "currency": "USD"}],
	"buy_credits": {"checkout": {"client_secret": "cs_demo_secret_demo", "key": "pk_test_demo"}, "credits": 500},
	"billing_card": {"checkout": {"client_secret": "cs_demo_secret_card", "key": "pk_test_demo"}},
	"plans_offered": {"plans": [{"name": "Team", "label": "Team", "seats": 10, "amount": 120}], "current": "Team"},
	"plans_quote": [{"plan": "Business", "extras": {}, "amount": 240}],
	"plans_take": {"plan": "Business", "amount": 240},
	"billed_to": {"billed_to": "huda@one.test"},
	"domain_list": [
		{"domain": "4dl.m.4dl.app", "status": "Active", "primary": 1, "given": 1},
		{"domain": "erp.saharaglass.com", "status": "Pending", "primary": 0},
	],
	"domain_refresh": [
		{"domain": "4dl.m.4dl.app", "status": "Active", "primary": 0, "given": 1},
		{"domain": "erp.saharaglass.com", "status": "Active", "primary": 1},
	],
	"domain_add": {"domain": "erp.saharaglass.com", "status": "Pending"},
	"domain_drop": {"domain": "erp.saharaglass.com"},
	"domain_primary": {"domain": "erp.saharaglass.com"},
	"billing_invoices": {"invoices": [{"number": "ONE-2026-0042", "amount": 120, "currency": "USD", "status": "paid"}]},
	"billing_portal": {"url": "https://billing.stripe.com/p/session/demo"},
	"billing_invoice": {
		"number": "ONE-2026-0042",
		"created": 1790812800,
		"currency": "USD",
		"seller": {"company_name": "Four Degree Labs", "country": "United Arab Emirates"},
		"lines": [{"description": "One Team plan, October", "amount": 120, "quantity": 1}, {"description": "Credit for September", "amount": -20}],
	},
}


def _account(method: str, **kwargs):
	return ACCOUNT.get(method.rsplit(".", 1)[-1])


@check
def the_plan_credits_domains_and_bills_are_the_administrators():
	"""Layla's Plan and Credits and Domains pages, with the account on the
	admin site answering as it would: credit packs and paying for one and a
	new card, both drawn in the page, a monthly limit, the
	plans offered, a quote and a change of plan, Huda made the payer, a
	domain added, made the main address and dropped, the bills from One
	listed and one put into the books as a purchase invoice. Omar may do
	none of it, and the build's wake call is answered for a guest."""
	from unittest import mock

	from onedesk.one import account
	from onedesk.account_center import bills

	with (
		as_user(OWNER),
		mock.patch("onedesk.one.account.ask", side_effect=_account),
		mock.patch("onedesk.one.account.configured", return_value=True),
		mock.patch("onedesk.one.account.refresh"),
	):
		assert account.credit_packs()[0]["label"] == "500 credits"
		assert account.buy_credits("credits-500")["checkout"]["client_secret"], "credits are paid for in the page"
		assert account.plans_offered()["current"] == "Team"
		assert account.plans_quote({"seats": 15})[0]["plan"] == "Business"
		assert account.plans_take("Business", {}, "Business")["plan"] == "Business"
		assert account.move_billing("huda@one.test")["billed_to"] == "huda@one.test"
		assert account.check_again()["ok"]
		assert [one["domain"] for one in account.domains()] == ["4dl.m.4dl.app", "erp.saharaglass.com"]
		assert account.domain_add("erp.saharaglass.com")["status"] == "Pending"
		assert account.domains_refresh()[1]["status"] == "Active"
		assert account.domain_primary("erp.saharaglass.com")["domain"] == "erp.saharaglass.com"
		account.domain_drop("erp.saharaglass.com")
		assert bills.invoices()["invoices"][0]["number"] == "ONE-2026-0042"
		assert bills.payment_portal()["url"].startswith("https://billing.stripe.com/")
		assert bills.change_card()["checkout"]["key"].startswith("pk_"), "a card is given in the page"
		with mock.patch("onedesk.one.account.ask", return_value={"limit": 2000}) as asked:
			assert bills.set_spend_limit(2000) == {"limit": 2000} and asked.call_args.kwargs == {"limit": 2000}
			bills.set_spend_limit(-5)
			assert asked.call_args.kwargs == {"limit": 0}, "a monthly limit is never below nothing"
			assert bills.set_update_window(0, 9) is not None and asked.call_args.kwargs == {"weekday": 0, "hour": 9}
			assert bills.update_now() is not None
		with mock.patch("onedesk.account_center.bills._attach"):
			bill = bills.to_books("ONE-2026-0042")
		made = frappe.get_doc("Purchase Invoice", bill)
		assert made.bill_no == "ONE-2026-0042" and made.discount_amount == 20 and made.docstatus == 0
		assert bills.to_books("ONE-2026-0042") == bill, "the same bill was booked twice"
	with as_user("omar@one.test"):
		try:
			account.plans_offered()
			raise AssertionError("Omar saw the plans")
		except frappe.PermissionError:
			pass
	frappe.set_user("Guest")
	_asked()
	with mock.patch("onedesk.one.account.configured", return_value=False):
		assert account.wake() == {"administered": False}


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
