"""One's part of the integration suite (one_demo/check.py runs it): the
workspace as a whole, its roles, rail, Homes and reports, signing in and
passkeys, settings, access, privacy, the bin, what notifications tell,
announcements, Help, tours and setup, and drawn pictures.

It stays one file past 1500 lines: the runner imports one checks.py a
module, and the guards read each module's checks by that name."""

import frappe
from frappe.utils import add_days, getdate, now_datetime, today

from onedesk.one_demo.base import COMPANY, as_user, on
from onedesk.one_demo.checking import (
	DESKTOP,
	PHONE,
	VILLA,
	_asked,
	_cookies,
	_each_way,
	_employee,
	_Phone,
	_refused,
	_Told,
	_unasked,
	check,
)
from onedesk.one_demo.people import OWNER, PEOPLE


def _reports():
	modules = frappe.get_all("Module Def", filters={"app_name": "onedesk"}, pluck="name")
	return frappe.get_all(
		"Report",
		filters={"module": ["in", modules], "report_type": ["in", ["Script Report", "Query Report"]], "is_standard": "Yes", "disabled": 0},
		pluck="name",
	)


FILTERS = {
	"company": COMPANY,
	"from_date": str(on(1, 1)),
	"to_date": today(),
	"date": today(),
	"month": getdate().month,
	"year": getdate().year,
	"fiscal_year": str(getdate().year),
	"period": "Monthly",
	"range": "Monthly",
}


@check
def every_report_of_ones_runs():
	from frappe.desk.query_report import run as run_report

	skip = {"AI Usage", "Plan Calculator", "Price Check", "AI Credits"}
	broken = []
	for name in _reports():
		if name in skip:
			continue
		try:
			with as_user(OWNER):
				run_report(name, filters=FILTERS)
		except Exception as e:
			broken.append((name, f"{type(e).__name__}: {e}"[:200]))
	assert not broken, broken


@check
def every_home_figure_reads_for_its_people():
	from onedesk.one import home
	from onedesk.one_book import home as books

	broken = []
	for user, calls in (
		("huda@one.test", (books.cash, books.profit_this_month, books.owed_to_us, books.overdue, books.we_owe, books.due_this_week)),
		*((email, (home.read, home.attention)) for _f, _l, email, *_r in PEOPLE if email),
	):
		for fn in calls:
			try:
				with as_user(user):
					fn()
			except Exception as e:
				broken.append((user, fn.__name__, f"{type(e).__name__}: {e}"[:160]))
	assert not broken, broken


@check
def every_rail_link_opens_for_its_app():
	from onedesk.one import reach

	refused = reach.unreachable()
	assert not refused, refused


@check
def the_demo_was_set_up_by_the_setup_job():
	"""Every step of the setup job is done, the builder is an administrator,
	and a wake starts nothing again."""
	from onedesk.one import setup_job
	from onedesk.one.roles import ADMINISTRATOR
	from onedesk.one_demo.setup import BUILDER

	assert set(setup_job.held().get("done") or []) == set(setup_job.ORDER), setup_job.held()
	assert ADMINISTRATOR in frappe.get_roles(BUILDER)
	assert frappe.db.get_single_value("System Settings", "country") == "United Arab Emirates"
	assert setup_job.wake() in ({"setup": "done"}, {"setup": "waiting"})


@check
def everybody_signs_in_to_what_they_were_given():
	"""Each person holds the roles People gave them, and only the owner and
	the person who set the workspace up are administrators."""
	from onedesk.one.roles import ADMINISTRATOR
	from onedesk.one_demo.setup import BUILDER

	admins = {u for u in frappe.get_all("Has Role", filters={"role": ADMINISTRATOR, "parenttype": "User"}, pluck="parent") if u.endswith("@one.test")}
	assert admins == {OWNER, BUILDER}, admins
	for _f, _l, email, *_r, access in PEOPLE:
		if email and access:
			assert frappe.db.get_value("User", email, "enabled"), email


@check
def a_manager_shares_what_they_assign():
	"""Assigning somebody a record they cannot open shares it with them."""
	with as_user("karim@one.test"):
		assert frappe.has_permission("Asset Maintenance", "share"), "Stock Manager cannot share upkeep"


@check
def nobody_is_turned_on_past_the_seats():
	from onedesk.one.people import seats_used

	frappe.db.set_value("User", "yousef@one.test", "enabled", 0)
	frappe.db.set_single_value("Workspace Account", "seats", seats_used())
	_refused(_each_way("Administrator", "User", "yousef@one.test", {"enabled": 1}), "seats are in use")


@check
def every_notification_file_is_on_the_notifications_page():
	"""Each file in onedesk/notifications/ is a type the workspace has, with
	the file's words, and listed for its administrator to change."""
	from onedesk.one import notification_words, notify, versions

	declared = notify.declared()
	with as_user(OWNER):
		listed = {one["name"] for app in notification_words._notification_types()["apps"] for one in app["types"]}
	missing = sorted(name for name, one in declared.items() if name not in listed and versions.offered(one["app"]))
	assert not missing, missing
	assert not {name for name, one in declared.items() if one["app"] == "OneAdmin"} & listed, "a workspace lists OneAdmin's types"
	wrong = [
		name
		for name, one in declared.items()
		if frappe.db.get_value("Notification Type", name, "one_default_subject") != notify.jinja(one.get("subject"))
	]
	assert not wrong, wrong


@check
def a_mail_says_what_happened_and_opens_it():
	"""A notification mailed to Karim is the workspace's, headed by what
	happened rather than frappe's "New Notification", with one button named
	for what it opens and which notification it is; a mail to an outside
	address is framed the same way, and one to a reader of Arabic right to
	left. Its button is the company's colour, and a mail One sends about
	itself wears One's mark. Its subject line reads as plain text."""
	from unittest import mock

	from onedesk.one import notify, tell

	subject, message = notify.render("Quote Received", {"supplier": "Emirates Sealants & Fixings", "request": "PUR-RFQ-2026-00005", "total": "4,975.00", "items": "Silicone"}, "en")
	log = frappe._dict(for_user="karim@one.test", type="Quote Received", subject=subject, email_content=message, document_type="Supplier Quotation", document_name="PUR-SQTN-1", link=None)
	with mock.patch("frappe.sendmail") as sent:
		notify.mail_log(log)
	said = sent.call_args.kwargs
	assert said["subject"] == "Emirates Sealants & Fixings sent a quote for PUR-RFQ-2026-00005", said["subject"]
	assert said["with_container"] and 'class="one-title"' in said["message"]
	assert "Open Supplier Quotation" in said["message"] and "/desk/supplier-quotation/PUR-SQTN-1" in said["message"]
	assert "<b>Quote Received</b>" in said["message"] and "center=notifications" in said["message"]
	assert "New Notification" not in said["message"]
	with mock.patch("frappe.sendmail") as sent:
		tell.portal_link("x@example.com", by="Karim", what="Quote Request R", workspace="W", link="https://x/l/1", button="Answer", until="1-1-2027")
	assert sent.call_args.kwargs["with_container"] and 'class="one-title"' in sent.call_args.kwargs["message"]
	from frappe.email.email_body import get_formatted_html

	framed = get_formatted_html("S", said["message"], with_container=True)
	assert frappe.utils.escape_html(notify.one_mail_brand()["name"]) in framed and "one-card" in framed
	assert "one-card" not in get_formatted_html("Re: your order", "<p>Hi</p>"), "a mail a person writes goes as written"
	arabic = get_formatted_html("S", notify.compose("S", "M", lang="ar"), with_container=True)
	assert arabic.count('dir="rtl"') >= 2, "a mail to a reader of Arabic reads right to left, masthead too"
	colour = frappe.db.get_value("Company", COMPANY, "one_brand_colour")
	assert colour.lower() in framed.lower(), "the button is the company's Brand Colour"
	ones = get_formatted_html("S", notify.compose("S", "M", ones=True), with_container=True)
	assert notify.ONE_MARK in ones and colour.lower() not in ones.lower(), "a mail about One wears One's mark"


@check
def the_payment_reminder_is_turned_on_where_every_notification_is():
	"""Send This on the Payment Reminder and the rule that mails it are one."""
	with as_user(OWNER):
		kind = frappe.get_doc("Notification Type", "Payment Reminder")
		kind.enabled = 1
		kind.save()
	assert frappe.db.get_value("Notification", "Payment Reminder", "enabled") == 1
	frappe.flags.in_import = True
	try:
		frappe.client.set_value("Notification", "Payment Reminder", "enabled", 0)
	finally:
		frappe.flags.in_import = False
	assert frappe.db.get_value("Notification Type", "Payment Reminder", "enabled") == 0


@check
def one_boards_open_on_frappes_new_kanban():
	"""The pipeline, the projects board and a project's own board open on
	frappe's new Kanban, each card showing One's fields by their icons
	(one/boards.py). erpnext's board of deals by status is gone, so the
	Pipeline is the one deal board."""
	from erpnext.projects.doctype.project.project import create_kanban_board_if_not_exists

	from onedesk.one_crm import board as pipeline
	from onedesk.one_project import board as projects

	villa = create_kanban_board_if_not_exists(VILLA)
	for name, card in ((pipeline.BOARD, pipeline.CARD), (projects.HEALTH_BOARD, projects.HEALTH_CARD), (villa, projects.CARD)):
		board = frappe.get_doc("Kanban Board", name)
		assert board.use_kanban_v2, f"{name} is on the old board"
		assert [(row.fieldname, row.icon) for row in board.card_fields] == list(card.items()), (name, board.card_fields)
	assert not frappe.db.exists("Kanban Board", pipeline.STATUS_BOARD), "erpnext's board of deals by status is back"
	assert frappe.db.get_value("Kanban Board", "Task Status", "is_standard") == "Yes", "erpnext's own task board"


@check
def one_offers_only_what_it_shows():
	"""A picker of record types or reports, which is also what a Dynamic Link
	asks first, and global search offer what One's rails, Homes and screens
	reach and never frappe's machinery; a dashboard a rail lists opens in that
	rail (one/outside.py, shown.json)."""
	from frappe.desk.doctype.sidebar.sidebar import linked_entities

	from onedesk.one import outside

	shown = outside.shown()
	picked = {row[0] for row in outside.doctype_query("DocType", "", "name", 0, 5000, {})}
	assert "Customer" in picked and "Employee" in picked, "a picker of record types leaves out One's own"
	assert not picked & {"DocType", "Module Def", "Workspace", "Custom Field", "Server Script"}, "a picker offers frappe's machinery"
	reports = {row[0] for row in outside.report_query("Report", "", "name", 0, 5000, {})}
	assert reports and reports <= shown["Report"], "a picker of reports offers one One does not show"
	found = outside.search("a", limit=50)
	assert all(row["doctype"] in shown["DocType"] for row in found), "global search finds a record type One does not show"
	ours = frappe.get_all("Sidebar", filters={"app": "onedesk"}, pluck="name")
	for item in frappe.get_all("Sidebar Item", filters={"parenttype": "Sidebar", "parent": ["in", ours]}, fields=["*"]):
		if item.type == "Link" and item.link_type in ("DocType", "Report", "Page", "Dashboard"):
			named = {one.split("/")[0] for one in linked_entities(item)}
			named = {one for one in named if frappe.db.exists(item.link_type, one)}
			missing = named - shown[item.link_type]
			assert not missing, f"{item.parent}'s rail links {sorted(missing)}, which One does not show"


@check
def the_owner_runs_the_setup_wizard():
	"""The wizard opens to whoever administers the workspace, asking again once
	it is done changes nothing, and this year's leave and payroll periods
	cover today (one/setup_wizard.py, one_hr/periods.py)."""
	from frappe.desk import desk_page

	from onedesk.one import roles, setup_wizard

	owner = roles.administrators()[0]
	frappe.set_user(owner)
	try:
		assert desk_page.get("setup-wizard"), "the wizard does not open for the workspace's administrator"
		assert setup_wizard.setup_complete("{}") == {"status": "ok"}
	finally:
		frappe.set_user("Administrator")
	day = frappe.utils.today()
	assert frappe.db.exists("Leave Period", {"from_date": ("<=", day), "to_date": (">=", day)}), "no leave year today"
	assert frappe.db.exists("Payroll Period", {"start_date": ("<=", day), "end_date": (">=", day)}), "no payroll year today"


@check
def one_an_app_turned_off_is_hidden_not_refused():
	"""The workspace administrator turns OneCRM off: it leaves everybody's
	rail, and Opportunity leaves search and the pickers, while Customer,
	which OneBook lists too, stays. Nothing is refused: an opportunity still
	opens, OneAI may still file into one, and turning OneCRM back
	on brings it all back. Nobody else may turn an app off."""
	from frappe.desk.doctype.dock.dock import resolve_dock

	from onedesk.one import apps

	with as_user("rania@one.test"):
		try:
			apps.save(["OneCRM"])
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("only a workspace administrator turns an app off")
	with as_user(OWNER):
		offered = {one["name"]: one for one in apps.read()["apps"]}
		assert "OneCRM" in offered and "One" not in offered, offered
		apps.save(["OneCRM"])
		assert apps.hidden() == ["OneCRM"]
		gone = set(apps.doctypes())
		assert "Opportunity" in gone and "Customer" not in gone, sorted(gone)[:20]
		picked = [one["value"] for one in apps.search_link("DocType", "Opportun")]
		assert "Opportunity" not in picked, picked
	rail = {row.get("link_to"): row.get("hidden") for row in resolve_dock().get("onedesk", [])}
	assert rail.get("OneCRM") in (None, 1) and not rail.get("OneBook"), rail
	opportunity = frappe.get_all("Opportunity", pluck="name", limit=1)
	assert opportunity and frappe.has_permission("Opportunity", "read", opportunity[0], user=OWNER)
	assert frappe.has_permission("Opportunity", "create", user=OWNER), "OneAI checks this before it files"
	with as_user(OWNER):
		apps.save([])
		assert not apps.doctypes()
		assert "Opportunity" in [one["value"] for one in apps.search_link("DocType", "Opportun")]


@check
def one_onebook_is_kept_once_it_has_entries_onecrm_is_not():
	"""The demo's books have ledger entries, so OneBook can't be turned off
	and Apps says why; OneCRM holds nothing the law or another app needs, so
	it turns off and back on. OneInventory is needed by OneFactory, and
	turning OneFactory on with OneInventory off brings it back on, said."""
	from onedesk.one import apps, registry

	book = registry.get("one_book")
	assert frappe.db.exists("GL Entry", {"docstatus": 1}), "the demo has books"
	with as_user(OWNER):
		offered = {one["name"]: one for one in apps.read()["apps"]}
		assert offered[book.sidebar]["held"], offered[book.sidebar]
		assert not offered["OneCRM"]["held"], offered["OneCRM"]
		assert offered["OneFactory"]["needs"] == ["OneInventory"], offered["OneFactory"]
		try:
			apps.save([book.sidebar])
		except frappe.ValidationError as refused:
			assert book.name in str(refused), refused
		else:
			raise AssertionError("OneBook was turned off with entries in it")
		assert book.sidebar not in apps.hidden()
		try:
			apps.save(["OneInventory"])
		except frappe.ValidationError as refused:
			assert registry.name("one_factory") in str(refused) or registry.get("one_inventory").name in str(refused), refused
		else:
			raise AssertionError("OneInventory was turned off with OneFactory on")
		try:
			apps.save(["OneCRM"])
			assert "OneCRM" in apps.hidden()
		finally:
			apps.save([])
		assert "OneCRM" not in apps.hidden()
		frappe.db.set_default(apps.KEY, '["OneFactory", "OneInventory"]')
		try:
			said = apps.save(["OneInventory"])["said"]
			assert not {"OneFactory", "OneInventory"} & set(apps.hidden()), apps.hidden()
			assert said and registry.name("one_inventory") in said[0], said
		finally:
			apps.save([])


@check
def one_marketplace_has_a_page_for_every_app_and_installs_into_setup():
	"""OneMarketplace shows every app with its words, plan and credits, for
	administrators only. OneBook can't be turned off there and says why;
	OneCRM turns off and installs again, landing in SetupCenter when it has
	steps; installing OneFactory with OneInventory off turns that on too."""
	from onedesk.one import apps, marketplace, registry

	with as_user("rania@one.test"):
		try:
			marketplace.read()
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("only a workspace administrator opens OneMarketplace")
	with as_user(OWNER):
		said = marketplace.read()
		pages = {one["id"]: one for one in said["apps"]}
		assert set(pages) == {one.id for one in registry.apps() if marketplace.shown(one)}, sorted(pages)
		assert all(one["pitch"] and one["brings"] and isinstance(one["pitch"], str) for one in pages.values())
		assert pages["one_book"]["kept"] and not pages["one_book"]["may_turn_off"], pages["one_book"]
		assert pages["one_ai"]["credits"], "OneAI says the credits it uses"
		try:
			marketplace.turn("one_crm", 0)
			assert registry.get("one_crm").sidebar in apps.hidden()
			back = marketplace.turn("one_crm", 1)
			has_steps = "one_crm" in marketplace._steps()
			assert bool(back["landing"]) == has_steps and (not has_steps or "center=setup" in back["landing"]), back
			frappe.db.set_default(apps.KEY, '["OneFactory", "OneInventory"]')
			brought = marketplace.turn("one_factory", 1)["said"]
			assert brought and registry.name("one_inventory") in brought[0], brought
		finally:
			apps.save([])


@check
def one_oneai_turned_off_asks_nothing_and_oneintake_reads_nothing():
	"""OneAI off, in Apps, turns OneAI off with it: no model is asked
	(`run.once`, a chat), nothing is queued to be read, no switch turns on,
	OneHR's screening is off, OneAI's rail leaves the dock, One's rail loses
	What OneAI Remembers and Reads, OneBook its Ready to Submit. Reading
	alone off leaves OneAI answering. What
	OneAI Reads holds only the reader's own mailboxes."""
	from frappe.boot import get_module_sidebars

	from onedesk.one import apps
	from onedesk.one_admin import faults
	from onedesk.one_ai import run, yours
	from onedesk.one_chat import panel
	from onedesk.one_ai.reading import pipeline, switches
	from onedesk.one_hr import hiring

	with as_user("rania@one.test"):
		mine = yours.load("reads")
		assert all(one["mine"] for one in mine["mailboxes"]), mine["mailboxes"]
	queued = []
	enqueue = frappe.enqueue
	frappe.enqueue = lambda *args, **kwargs: queued.append(args)
	try:
		with as_user(OWNER):
			apps.save(["OneAI", "OneStudio"])
			assert {"OneAI", "Reading", "OneStudio"} <= set(apps.hidden()), apps.hidden()
			try:
				run.once("chat_title", "anything")
			except faults.Refused:
				pass
			else:
				raise AssertionError("OneAI off still asked a model")
			try:
				panel.say("hello")
			except frappe.ValidationError:
				pass
			else:
				raise AssertionError("OneAI off still started a chat")
			pipeline.later("read_file", "file:nothing", name="nothing", person=OWNER)
			assert not queued, queued
			box = frappe.get_all("Email Account", pluck="name", limit=1)
			if box:
				try:
					switches.set_mailbox(box[0], 1)
				except frappe.ValidationError:
					pass
				else:
					raise AssertionError("a mailbox switched on with OneAI off")
			assert not hiring.on("one_ai_screen")
			from frappe.desk.doctype.dock.dock import resolve_app_dock

			assert "OneAI" not in [one.get("link_to") for one in resolve_app_dock(apps.HOST) if not one.get("hidden")]
			sidebars = get_module_sidebars()
			apps.trim(sidebars)
			urls = {item.get("url") for item in sidebars["One"]["items"]}
			assert not urls & {"/desk/one?center=ai&at=yours", "/desk/one?center=ai&at=reads"}, urls
			assert "One Intake" not in sidebars
			assert all(item.get("link_to") != "Ready to Submit" for item in (sidebars.get("OneBook") or {}).get("items", []))
			apps.save(["Reading"])
			assert apps.ai_on() and not apps.intake_on()
			apps.save([])
			assert apps.intake_on() and hiring.on("one_ai_screen") == bool(frappe.db.get_single_value("HR Settings", "one_ai_screen"))
	finally:
		frappe.enqueue = enqueue
		with as_user(OWNER):
			apps.save([])


@check
def one_an_app_at_no_level_is_never_offered():
	"""Samir holds no level in OneBook: its sidebar leaves his boot, so it is
	on no rail, launcher or search of his, its Help is off, and AccessCenter
	is not among his centres. Huda, who manages OneBook, keeps it all
	(one/rail.py)."""
	from frappe.boot import get_module_sidebars

	from onedesk.one import outside, rail, registry, versions

	book = registry.get("one_book")
	for user, sees in (("samir@one.test", False), ("huda@one.test", True)):
		with as_user(user):
			assert (book.sidebar in rail.unreached()) is not sees, user
			said = {"module_sidebars": get_module_sidebars(), "entity_module": {}, "user": {}}
			outside.kept(said)
			assert (book.sidebar in said["module_sidebars"]) is sees, (user, list(said["module_sidebars"]))
			assert bool(versions.for_boot().get(book.name, {}).get("off")) is not sees, user
			boot = {"module_sidebars": said["module_sidebars"], "one_centres": [{"key": "access"}, {"key": "help"}, {"key": "settings"}]}
			rail.boot(boot)
			keys = {one["key"] for one in boot["one_centres"]}
			assert "settings" in keys and "help" in keys and "access" not in keys, (user, keys)


@check
def one_a_persons_order_and_folders_outlast_the_workspaces():
	"""Rania reverses her rail (frappe's save_user_dock) and puts two apps in
	a folder; the administrator then sets the workspace's order. Rania keeps
	hers and her folder; Reset puts her on the workspace's order."""
	import json

	from frappe.desk.doctype.dock.dock import resolve_app_dock, save_user_dock
	from frappe.model.utils.user_settings import save as keep

	from onedesk.one import rail

	shown = lambda rows: [rail._key(one) for one in rows if not one.get("hidden")]  # noqa: E731
	person = "rania@one.test"
	try:
		with as_user(person):
			mine = [one for one in resolve_app_dock(rail.HOST) if not one.get("hidden")]
			order = list(reversed(mine))
			save_user_dock(rail.HOST, json.dumps([{"link_type": one["link_type"], "link_to": one.get("link_to"), "url": one.get("url")} for one in order]))
			keep(rail.SETTINGS, {"folders": [{"name": "Work", "apps": shown(order[:2])}]})
		with as_user(OWNER):
			workspace = [one["key"] for one in rail.workspace()["apps"]]
			workspace = workspace[1:] + workspace[:1]
			rail.save_workspace(workspace)
		with as_user(person):
			boot = {"module_sidebars": {}, "dock": {rail.HOST: resolve_app_dock(rail.HOST)}}
			rail.boot(boot)
			assert shown(boot["dock"][rail.HOST]) == shown(order), shown(boot["dock"][rail.HOST])
			assert boot["one_rail"]["folders"] == [{"name": "Work", "apps": shown(order[:2])}], boot["one_rail"]
			save_user_dock(rail.HOST, "[]")
			now = shown(resolve_app_dock(rail.HOST))
			assert now == [key for key in workspace if key in now], now
	finally:
		with as_user(person):
			keep(rail.SETTINGS, {"folders": [], "recent": []})
			save_user_dock(rail.HOST, "[]")
		with as_user(OWNER):
			rail.save_workspace([])


@check
def one_a_person_works_in_one_company_at_a_time():
	"""With Sahara Glass Saudi beside Sahara, Karim may switch between them
	from the frame, and Stock Summary follows; a company he may not read is
	refused, and Yousef, who reads no company, is offered none."""
	from onedesk.one import company
	from onedesk.one_demo.branch import BRANCH
	from onedesk.one_inventory import stock

	try:
		with as_user("karim@one.test"):
			said = company.mine()
			assert said and {COMPANY, BRANCH} <= set(said["all"]) and said["current"] == COMPANY, said
			company.use(BRANCH)
			assert company.mine()["current"] == BRANCH and stock.on_hand()["currency"] == "SAR"
			try:
				company.use("No Such Company")
				raise AssertionError("a company he may not work in was taken")
			except frappe.PermissionError:
				pass
	finally:
		frappe.defaults.set_user_default("company", COMPANY, "karim@one.test")
	with as_user("yousef@one.test"):
		assert company.mine() is None


@check
def one_the_frame_wears_the_workspace_colour():
	"""Frame Colour in One's ControlCenter › Branding is the rail and the bars
	around every screen, for everyone; saved empty, the frame is One's own."""
	from onedesk.one import company, control

	was = frappe.db.get_value("Company", COMPANY, "one_frame_colour")
	try:
		control._save_general({"one_frame_colour": "#7C2D12"})
		assert company.frame_colour() == "#7C2D12", "the frame did not take the workspace's colour"
		control._save_general({"one_frame_colour": ""})
		assert not company.frame_colour(), "an emptied Frame Colour still coloured the frame"
	finally:
		frappe.db.set_value("Company", COMPANY, "one_frame_colour", was)


@check
def one_a_private_app_is_always_on():
	"""A private app installed has a card in Apps that can't be turned off,
	and uninstalling it is refused."""
	from unittest.mock import patch

	from onedesk.one import apps
	from onedesk.account_center import private

	said = {"name": "acme_fleet", "title": "Acme Fleet", "said": "Acme's vans.", "icon": "truck"}
	with patch.object(private, "names", return_value=["acme_fleet"]), patch.object(private, "about", return_value=said), patch.object(private, "rail", return_value=set()):
		card = next(one for one in apps.offered() if one["name"] == "acme_fleet")
		assert card["kept"] and card["on"], card
		with as_user(OWNER):
			try:
				apps.save(["acme_fleet"])
			except frappe.ValidationError:
				pass
			else:
				raise AssertionError("a private app was turned off")
		try:
			private.refuse_uninstall("acme_fleet")
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("a private app was uninstalled")
		private.refuse_uninstall("hrms")


@check
def one_devices_decide_where_a_passkey_lives():
	"""Signing in gives a browser its id and lists it. The builder sorts two:
	the reception computer, shared, where Tariq is neither offered nor allowed
	a passkey; and his laptop, assigned, which takes one beside his phone's
	that signs for him. Lost retires the laptop's and leaves the phone's."""
	import json

	from onedesk.account_center import devices
	from onedesk.account_center.signin import facts
	from onedesk.one_demo.setup import BUILDER
	from onedesk.one_hr import passkey, signin

	tariq = _employee("Tariq")
	frappe.db.set_single_value("System Settings", signin.SWITCH, 1)
	frappe.db.set_single_value("HR Settings", "one_self_checkin", 1)
	frappe.db.delete("Clock Device", {"user": "tariq@one.test"})

	def signs_in(user, agent, cookies=None):
		with as_user(user):
			frappe.session.sid = frappe.generate_hash()
			_asked(headers={"User-Agent": agent}, cookies=cookies)
			devices.signed_in(None)
		return {devices.COOKIE: frappe.local.cookie_manager.cookies[devices.COOKIE]["value"]}

	reception_browser = signs_in(BUILDER, DESKTOP)
	laptop_browser = signs_in("tariq@one.test", DESKTOP)
	assert signs_in("tariq@one.test", DESKTOP, laptop_browser) == laptop_browser, "a second sign-in made a second device"
	with as_user(BUILDER):
		_asked(headers={"User-Agent": DESKTOP}, cookies=reception_browser)
		reception = devices.here().name
		_asked(headers={"User-Agent": DESKTOP}, cookies=laptop_browser)
		laptop = devices.here().name
		listed = {one["name"]: one for one in devices.for_settings()["devices"]}
		assert listed[laptop]["seen_by"] and not listed[laptop]["use"]
		_asked(headers={"User-Agent": DESKTOP}, cookies=reception_browser)
		frappe.db.delete("Clock Device", {"user": BUILDER})
		builder = _Phone(b"builder")
		passkey.finish_registration(json.dumps(builder.make(passkey.start_registration())), {"user_agent": DESKTOP})
		with _Told() as told:
			assert devices.save(reception, "Reception Computer", "Shared")["retired"] == 1
		assert not passkey.held(BUILDER), "a passkey still works on the shared computer"
		assert told.to("Passkey Turned Off") == {BUILDER}, told.said
		devices.save(laptop, "Tariq's Laptop", "Assigned", "tariq@one.test")

	with as_user("tariq@one.test"):
		_asked(headers={"User-Agent": DESKTOP}, cookies=reception_browser)
		assert not passkey.ask(), "offered a passkey on the shared computer"
		try:
			passkey.start_registration()
			raise AssertionError("a passkey was made on the shared computer")
		except frappe.ValidationError:
			pass

		phone, desk = _Phone(b"t-phone"), _Phone(b"t-desk")
		_asked(headers={"User-Agent": PHONE})
		passkey.finish_registration(json.dumps(phone.make(passkey.start_registration())), {"user_agent": PHONE})
		_asked(headers={"User-Agent": DESKTOP}, cookies=laptop_browser)
		assert passkey.ask() and facts()["add_here"], "not offered a passkey on his own laptop"
		made = passkey.finish_registration(json.dumps(desk.make(passkey.start_registration())), {"user_agent": DESKTOP})
		assert frappe.db.get_value("Clock Device", made["device"], "device") == laptop
		_asked(headers={"User-Agent": DESKTOP}, cookies=laptop_browser)
		try:
			passkey.start_registration()
			raise AssertionError("two passkeys on one laptop")
		except frappe.ValidationError:
			pass
		_asked(headers={"User-Agent": DESKTOP}, cookies=laptop_browser)
		options = passkey.start_assertion()
		assert len(options["allowCredentials"]) == 2
		_asked(headers={"User-Agent": DESKTOP}, cookies=laptop_browser)
		signed = passkey.check(json.dumps(desk.sign(options)), tariq)
		assert signed["device"] == made["device"] and signed["verified"], signed

	with as_user(BUILDER):
		_asked(headers={"User-Agent": DESKTOP})
		assert devices.lost(laptop)["retired"] == 1
		devices.retire(reception)
	assert passkey.held("tariq@one.test"), "the phone's passkey went with the laptop"
	with as_user(BUILDER):
		_asked(headers={"User-Agent": DESKTOP})
		listed = devices.for_settings()["passkeys"]
		phone_key = next(one["name"] for one in listed if one["person"] == frappe.utils.get_fullname("tariq@one.test"))
		with _Told() as told:
			devices.retire_passkey(phone_key)
		assert told.to("Passkey Turned Off") == {"tariq@one.test"}
	assert not passkey.held("tariq@one.test")
	devices.forget()
	_unasked()


@check
def one_anybody_signs_in_with_a_passkey():
	"""Not only employees: the workspace's builder, who is none, is offered a
	passkey after signing in, makes one on a computer, signs in with it, and
	removes it themselves. An employee the clock checks cannot remove theirs."""
	import json
	from unittest import mock

	from onedesk.one_demo.setup import BUILDER
	from onedesk.one_hr import passkey, signin

	frappe.db.set_single_value("System Settings", signin.SWITCH, 1)
	frappe.db.set_single_value("HR Settings", "one_self_checkin", 1)
	frappe.db.delete("Clock Device", {"user": BUILDER})
	laptop = _Phone(BUILDER.encode())
	with as_user(BUILDER):
		frappe.defaults.clear_user_default("one_passkey_asked", BUILDER)
		_asked(headers={"User-Agent": DESKTOP})
		assert passkey.ask()
		passkey.not_now()
		assert not passkey.ask(), "asked again the same week"
		made = passkey.finish_registration(json.dumps(laptop.make(passkey.start_registration())), {"user_agent": DESKTOP})
		assert frappe.db.get_value("Clock Device", made["device"], ["user", "employee"]) == (BUILDER, None)

	frappe.set_user("Guest")
	_asked(headers={"User-Agent": DESKTOP})
	options = signin.begin()
	_asked(headers={"User-Agent": DESKTOP}, cookies=_cookies())
	frappe.local.login_manager = mock.Mock()
	assert signin.finish(json.dumps(laptop.sign(options)))["user"] == BUILDER

	with as_user(BUILDER):
		_asked(headers={"User-Agent": DESKTOP})
		assert passkey.remove()["removed"] == 1 and not passkey.held(BUILDER)
	with as_user("tariq@one.test"):
		_asked(headers={"User-Agent": PHONE})
		try:
			passkey.remove()
			raise AssertionError("an employee the clock checks removed their own passkey")
		except frappe.ValidationError:
			pass
	frappe.db.set_single_value("HR Settings", "one_self_checkin", 0)
	frappe.db.delete("Clock Device", {"user": "tariq@one.test"})
	with as_user("tariq@one.test"):
		_asked(headers={"User-Agent": DESKTOP})
		assert not passkey.ask(), "offered a passkey on a computer"
		try:
			passkey.start_registration()
			raise AssertionError("an employee registered a passkey on a computer")
		except frappe.ValidationError:
			pass
	_unasked()


@check
def settings_open_and_save_for_each_person():
	"""Every centre's section opens for Layla and only Rania's own for her.
	Rania's stale save is refused; Layla saves General and Holidays, invites
	Hana, turns Nadia off and on, and drops a rule OneAI wrote. What OneAI
	remembers is kept and forgotten."""
	from onedesk.one import access_center, ai_notifications, audit, control, notification_words, privacy, rules
	from onedesk.account_center import center
	from onedesk.one_ai import run as runs
	from onedesk.one_ai import yours
	from onedesk.one_calendar import control as calendar_control
	from onedesk.one_hr import control as hr_control
	from onedesk.one_studio import control as studio_control

	with as_user("rania@one.test"):
		assert "link" in calendar_control.load("link") and yours.load("reads") is not None
		for refused in (control.sections_of, lambda: control.load("general"), lambda: hr_control.load("holidays"), lambda: access_center.load("access"), lambda: studio_control.load("numbering"), lambda: notification_words.load("words")):
			try:
				refused()
				raise AssertionError("Rania opened a workspace setting")
			except frappe.PermissionError:
				pass
		hers = center.sections_of()
		assert {one["group"] for one in hers["sections"]} == {"yours"}
		for one in hers["sections"]:
			center.load(one["key"])
		try:
			center.load("people")
			raise AssertionError("Rania opened People")
		except frappe.PermissionError:
			pass
		loaded = center.load("profile")
		center.save("profile", {"mobile_no": "+971 50 555 0142"}, loaded["opened"])
		assert frappe.db.get_value("User", "rania@one.test", "mobile_no") == "+971 50 555 0142"
		stale = [{**one, "modified": "2020-01-01 00:00:00"} for one in loaded["opened"]]
		try:
			center.save("profile", {"mobile_no": "+971 50 555 0199"}, stale)
			raise AssertionError("a stale page overwrote a newer save")
		except frappe.TimestampMismatchError:
			pass
		kept = yours.keep("I prefer replies in Arabic.")
		memory = next(one["name"] for one in kept["facts"] if one["fact"] == "I prefer replies in Arabic.")
		yours.forget(memory)
		yours.keep("I work from the Bayview site on Tuesdays.")
		yours.forget_all()
		assert not frappe.db.exists("AI Memory", {"owner": "rania@one.test"})
		assert center.sign_out_elsewhere() == 1
	with as_user(OWNER):
		for key, *_rest in studio_control.SECTIONS:
			studio_control.load(key)
		from frappe.core.doctype.activity_log.activity_log import add_authentication_log

		add_authentication_log("Signed in", "rania@one.test")
		assert {one["kind"] for one in audit.log()} >= {"changes", "signins"}, "the Audit Log misses a kind"
		assert all(one["kind"] == "changes" for one in audit.log("changes", 10))
		assert set(privacy.requests()) == {"deletions", "copies"}
		notification_words.load("words")
		assert [one["key"] for one in control.sections_of()["sections"]] == ["company", "branding", "formats", "signin", "sharing", "pictures"]
		for key in ("company", "branding", "formats", "signin", "sharing"):
			tab = control.load(key)
			assert set(tab["values"]) <= set(control.HOLDS[key]), f"{key} carries another tab's values"
			control.save(key, {}, tab["opened"])
		holidays = hr_control.load("holidays")
		hr_control.save("holidays", holidays["values"], holidays.get("opened"))
		assert access_center.load("access")["levels"]
		for one in center.sections_of()["sections"]:
			center.load(one["key"])
		center.invite("hana@one.test", "Hana", "Rizk", {"OneCRM": "User"})
		assert frappe.db.exists("User", "hana@one.test")
		center.invite_again("hana@one.test")
		center.set_enabled("nadia@one.test", 0)
		assert frappe.db.get_value("User", "nadia@one.test", "enabled") == 0
		center.set_enabled("nadia@one.test", 1)
		center.send_reset("nadia@one.test")
		center.sign_out_everywhere("nadia@one.test")
		from unittest import mock

		from onedesk.account_center import signin

		was = frappe.db.get_single_value("System Settings", "enable_two_factor_auth")
		frappe.db.set_single_value("System Settings", "enable_two_factor_auth", 1)
		try:
			with mock.patch("onedesk.one.tell.two_factor_reset") as told:
				center.reset_two_factor("nadia@one.test")
				with as_user("rania@one.test"):
					signin.reset_two_factor()
			assert [one.args[0] for one in told.call_args_list] == ["nadia@one.test", "rania@one.test"]
		finally:
			frappe.db.set_single_value("System Settings", "enable_two_factor_auth", was)
		assert rules.fields_of("Sales Invoice")
		assert rules.watchable("DocType", "Sales", "name", 0, 20)
		drafted = ai_notifications.draft_notification("Big Invoice", "Sales Invoice", "Submit", "Invoice {{ doc.name }} is out", roles=["Accounts Manager"])
		runs.apply(drafted["proposal"])
		rule = frappe.db.get_value("Notification", {"one_rule": 1, "document_type": "Sales Invoice", "event": "Submit"})
		assert rule, "the rule was not made"
		kind = frappe.db.get_value("Notification Type", {"one_rule": rule})
		typed = notification_words.load("words", kind)
		notification_words.save("words", typed.get("values") or {}, typed.get("opened"), kind)
		assert "html" in notification_words.preview_notification(kind, "Invoice {{ doc.name }}") or notification_words.preview_notification(kind, "Invoice {{ doc.name }}")
		notification_words.delete_rule(rule)
		assert not frappe.db.exists("Notification", rule)


@check
def access_is_shaped_by_the_administrator():
	"""Layla makes a level between User and Manager, a job profile and a
	group, and holds Omar to one customer, after which he sees only that
	one; each goes again. OneAI suggests a level, a profile, a group, a hold,
	a saved report, a dashboard and a report by mail, and each card applied
	is there afterwards. Omar may do none of it."""
	from onedesk.one import access, access_center
	from onedesk.one_ai import run as runs
	from onedesk.one_studio import ai_setup

	customers = frappe.get_all("Customer", pluck="name", order_by="name asc")
	with as_user("omar@one.test"):
		assert len(frappe.get_list("Customer", pluck="name")) == len(customers)
		try:
			access.make_level("OneCRM", "Senior Sales")
			raise AssertionError("Omar made a level")
		except frappe.PermissionError:
			pass
	with as_user(OWNER):
		level = access.make_level("OneCRM", "Senior Sales")
		for refused, said in (
			(lambda: access.save_level(level, "Senior Sales", [{"doctype": "Salary Slip", "read": 1}]), "is not a record type"),
			(lambda: access.hold("omar@one.test", "Company", COMPANY), ""),
		):
			try:
				refused()
			except frappe.ValidationError as e:
				assert said in str(e), e
			else:
				raise AssertionError(f"a level or a hold reached past its app: {said}")
		assert level in {key for app in access.doctype_levels("Opportunity") for row in app["rows"] for key in (row["level"], row["key"])}, access.doctype_levels("Opportunity")
		access.remove_level(level)
		profile = access.new_profile("Estimator")
		assert frappe.db.exists("Role Profile", profile)
		opened = access_center.load("access", f"profile:{profile}")
		access_center.save("access", {"app_onecrm": "User"}, opened.get("opened"), f"profile:{profile}")
		assert access.profile(profile)["levels"].get("OneCRM") == "User", "AccessCenter did not save the profile"
		access.remove_profile(profile)
		group = access.new_group("Site Team", ["rania@one.test", "tariq@one.test"])
		assert frappe.db.count("User Group Member", {"parent": group}) == 2
		access.remove_group(group)
		access.hold("omar@one.test", "Customer", customers[0])
		held = frappe.db.get_value("User Permission", {"user": "omar@one.test", "allow": "Customer", "for_value": customers[0]})
	with as_user("omar@one.test"):
		assert frappe.get_list("Customer", pluck="name") == [customers[0]]
	with as_user(OWNER):
		access.let_go(held)
	with as_user("omar@one.test"):
		assert len(frappe.get_list("Customer", pluck="name")) == len(customers)

	with as_user(OWNER):
		cards = [
			ai_setup.suggest_level("OneCRM", "Senior Sales", give=[{"doctype": "Quotation", "rights": ["read", "edit", "submit"]}], starts_as="User"),
			ai_setup.suggest_profile("Estimator", {"OneCRM": "User", "OneProject": "User"}),
			ai_setup.suggest_group("Site Team", ["rania@one.test", "tariq@one.test"]),
			ai_setup.suggest_hold("omar@one.test", "Customer", customers[0], only_on="Quotation"),
			ai_setup.suggest_saved_report("Sales Invoice", "Unpaid Invoices", ["name", "customer", "outstanding_amount"], [["outstanding_amount", ">", 0]], totals=True),
			ai_setup.suggest_dashboard("Sales", [{"title": "Invoiced by month", "doctype": "Sales Invoice", "measure": "sum", "field": "grand_total", "over_time": "posting_date", "interval": "Monthly", "timespan": "Last Year"}]),
			ai_setup.suggest_report_mail("Accounts Receivable", ["huda@one.test"], "Weekly", "Monday"),
		]
		for card in cards:
			assert card.get("proposal"), card
			runs.apply(card["proposal"])
			assert frappe.db.get_value("AI Proposal", card["proposal"], "state") == "Applied", card
	assert frappe.db.exists("Role", {"role_name": ["like", "%Senior Sales%"]})
	assert frappe.db.exists("Role Profile", "Estimator") and frappe.db.exists("User Group", "Site Team")
	assert frappe.db.exists("User Permission", {"user": "omar@one.test", "for_value": customers[0], "applicable_for": "Quotation"})
	assert frappe.db.exists("Report", {"report_name": "Unpaid Invoices"}) and frappe.db.exists("Dashboard", "Sales")
	assert frappe.db.exists("Auto Email Report", {"report": "Accounts Receivable"})


def _opened_link(url: str) -> None:
	"""A link someone was mailed, opened in their browser."""
	from urllib.parse import urlsplit

	parts = urlsplit(url)
	_asked(path=f"{parts.path}?{parts.query}", method="GET")
	frappe.local.form_dict = frappe._dict(frappe.local.request.args.items())


@check
def privacy_requests_go_through_the_administrators():
	"""Nadia asks for her account to be deleted, Layla holds it with a reason
	and then approves it; Tariq asks and changes his mind; Yousef, who signs
	in without a password, confirms by the link he is mailed. Rania asks for
	a copy of her data and Layla sends it withholding her notes. Somebody who
	is not a user asks from the public page, confirms by mail and downloads
	the copy; a link that was not signed by the workspace opens nothing."""
	from unittest import mock

	from onedesk.one import privacy, privacy_copy, privacy_public

	mailed = {}
	def keep(key):
		return lambda *args, **kw: mailed.__setitem__(key, next(one for one in args if isinstance(one, str) and "/api/method/" in one))

	with mock.patch("frappe.utils.password.check_password"), mock.patch("frappe.enqueue"):
		with as_user("nadia@one.test"):
			privacy.ask_to_delete("her password")
		nadia = frappe.db.get_value(privacy.DELETION, {"email": "nadia@one.test"})
		with as_user("tariq@one.test"):
			privacy.ask_to_delete("his password")
			privacy.withdraw()
			assert not frappe.db.exists(privacy.DELETION, {"email": "tariq@one.test"})
		with as_user(OWNER):
			privacy.hold(nadia, "Her timesheets are still being invoiced this month.")
			assert frappe.db.get_value(privacy.DELETION, nadia, "status") == "On Hold"
			privacy.approve(nadia)
			assert frappe.db.get_value("User", "nadia@one.test", "enabled") == 0
		with as_user("yousef@one.test"), mock.patch("onedesk.one.privacy._has_password", return_value=False), mock.patch("onedesk.one.tell.asked_to_confirm_deletion", side_effect=keep("delete")):
			privacy.ask_to_delete()
		frappe.set_user("Guest")
		_opened_link(mailed["delete"])
		privacy.confirm(frappe.local.form_dict.name, frappe.local.form_dict.expires)
		assert frappe.db.get_value(privacy.DELETION, {"email": "yousef@one.test"}, "status") == "Pending Approval"

		with as_user("rania@one.test"):
			privacy_copy.ask()
		copy = frappe.db.get_value(privacy_copy.DOWNLOAD, {"user": "rania@one.test", "one_status": "Waiting"})
		with as_user(OWNER):
			kinds = {one["key"] for one in privacy_copy.review(copy)["kinds"]}
			assert "account" in kinds
			optional = [key for key, _label, always in privacy_copy.kinds_for("rania@one.test") if not always]
			privacy_copy.send(copy, optional[:1], "Kept while the audit is open.")
			assert frappe.db.get_value(privacy_copy.DOWNLOAD, copy, "one_status") == "Gathering"

		frappe.cache.delete_keys("rl:")
		frappe.set_user("Guest")
		with mock.patch("onedesk.one.tell.request_to_confirm", side_effect=keep("public")):
			privacy_public.ask("jordan@acme.example", "copy")
		_opened_link(mailed["public"])
		privacy_public.confirm(frappe.local.form_dict.email, frappe.local.form_dict.kind, frappe.local.form_dict.expires)
		outsider = frappe.db.get_value(privacy_copy.DOWNLOAD, {"one_email": "jordan@acme.example"})
		assert outsider
		with as_user(OWNER):
			privacy_copy.send(outsider)
		frappe.set_user("Administrator")
		with mock.patch("onedesk.one.tell.copy_ready_to_download"):
			privacy_copy.gather(outsider)
		frappe.set_user("Guest")
		link = privacy_public._signed("download", request=outsider, expires=str(add_days(today(), 7)) + " 00:00:00")
		_opened_link(link)
		privacy_public.download(frappe.local.form_dict.request, frappe.local.form_dict.expires)
		given = frappe.local.response.filecontent
		assert "jordan@acme.example" in (given.decode() if isinstance(given, bytes) else given)
		_opened_link(link.replace("_signature=", "_signature=0"))
		frappe.local.response.pop("filecontent", None)
		privacy_public.download(frappe.local.form_dict.request, frappe.local.form_dict.expires)
		assert not frappe.local.response.get("filecontent")
	_unasked()


@check
def privacy_holds_each_person_to_their_own():
	"""Only administrators read the requests. Asking needs the person's own
	password, and nobody who pays for the workspace, nor its last
	administrator, may go, nor approve their own going. Everybody concerned
	is told. A copy withholds only what may be withheld, and says why; it is
	kept on the person's account, and is gone when they are. Approving signs
	the person out and turns them off, and erasing does what frappe does,
	for somebody who is not a user too. A public page answers the same
	whether the address is known or not."""
	from unittest import mock

	from onedesk.one import privacy, privacy_copy, privacy_public

	with as_user("nadia@one.test"), mock.patch("frappe.utils.password.check_password", side_effect=frappe.AuthenticationError):
		try:
			privacy.ask_to_delete("not my password")
		except frappe.ValidationError as e:
			assert "not your password" in str(e), e
		else:
			raise AssertionError("an account was asked to be deleted with a wrong password")
	frappe.db.set_single_value("Workspace Account", "billed_to", OWNER)
	with as_user(OWNER), mock.patch("frappe.utils.password.check_password"):
		try:
			privacy.ask_to_delete("her password")
		except frappe.ValidationError as e:
			assert "billed to this account" in str(e), e
		else:
			raise AssertionError("whoever pays asked to be deleted")

	with _Told() as told, mock.patch("frappe.utils.password.check_password"), mock.patch("frappe.enqueue") as queued:
		with as_user("nadia@one.test"):
			privacy.ask_to_delete("her password")
		assert told.to("Deletion Asked") >= {OWNER}, told.said
		nadia = frappe.db.get_value(privacy.DELETION, {"email": "nadia@one.test"})
		for user, may in ((OWNER, True), ("rania@one.test", False)):
			assert bool(frappe.has_permission(privacy.DELETION, "read", doc=nadia, user=user)) == may, user
		with as_user(OWNER):
			privacy.hold(nadia, "Her timesheets are still being invoiced this month.")
			assert "nadia@one.test" in told.to("Deletion On Hold"), told.said
			frappe.db.sql("insert into `tabSessions` (user, sid, sessiondata, lastupdate, status) values ('nadia@one.test', 'demo-nadia', '{}', now(), 'Active')")
			privacy.approve(nadia)
		assert frappe.db.get_value("User", "nadia@one.test", "enabled") == 0 and queued.called
		assert not frappe.db.sql("select 1 from `tabSessions` where user = 'nadia@one.test'"), "approving signs them out"

		with as_user("rania@one.test"):
			privacy_copy.ask()
		assert told.to("Copy Asked") >= {OWNER}, told.said
		copy = frappe.db.get_value(privacy_copy.DOWNLOAD, {"user": "rania@one.test", "one_status": "Waiting"})
		always = [key for key, _label, kept in privacy_copy.kinds_for("rania@one.test") if kept]
		optional = [key for key, _label, kept in privacy_copy.kinds_for("rania@one.test") if not kept]
		with as_user(OWNER):
			for withheld, why in ((always[:1], "No."), (optional[:1], None)):
				try:
					privacy_copy.send(copy, withheld, why)
				except frappe.ValidationError:
					pass
				else:
					raise AssertionError(f"a copy withheld {withheld} with {why!r}")
			privacy_copy.send(copy, optional[:1], "Kept while the audit is open.")
	frappe.set_user("Administrator")
	with _Told() as told:
		privacy_copy.gather(copy, optional[:1])
	assert "rania@one.test" in told.to("Your Data Is Ready"), told.said
	assert frappe.db.exists("File", {"attached_to_doctype": "User", "attached_to_name": "rania@one.test", "file_name": ["like", "Personal-Data-%"]})

	privacy.erase(nadia)
	assert not frappe.db.exists("User", "nadia@one.test"), "frappe's erasure renames the account"

	frappe.cache.delete_keys("rl:")
	frappe.set_user("Guest")
	_asked(path="/", method="POST")
	with mock.patch("onedesk.one.tell.request_to_confirm"):
		assert privacy_public.ask("khalid@mansour.example", "delete") == privacy_public.ask("nobody@nowhere.example", "delete"), "the page says whether it knows an address"
	frappe.set_user("Administrator")
	outsider = frappe.get_doc({"doctype": privacy.DELETION, "email": "khalid@mansour.example", "status": "Pending Approval"})
	outsider.set_new_name()
	outsider.db_insert()
	mentioned = frappe.db.count("Contact", {"email_id": "khalid@mansour.example"})
	assert mentioned, "the demo's customer contact"
	privacy.erase(outsider.name)
	assert not frappe.db.count("Contact", {"email_id": "khalid@mansour.example"}), "frappe's redaction left the address"
	assert frappe.db.get_value(privacy.DELETION, outsider.name, "status") == "Deleted"
	_unasked()


@check
def the_one_home_lists_and_the_bin_answer_for_their_people():
	"""The One home's figures as Samir and as Layla, what needs Layla's
	attention, a saved report placed in OneCRM's sidebar for everybody,
	every module's lists read, added to and counted, next
	year's holidays made and put in force with the country's own public
	holidays, and a deleted project task brought back from the bin."""
	from onedesk.one import home, lists, recycle
	from onedesk.one_hr import holidays
	from onedesk.one_studio import reports

	with as_user("samir@one.test"):
		said = home.read()
		assert said["waiting"] >= len(said["approvals"]), said
		assert all(one["title"] for one in said["announcements"]), said["announcements"]
		assert not said["needs"] and not said["glance"] and not said["administers"], "Samir is told about the workspace"
	with as_user(OWNER):
		assert isinstance(home.attention(), list)
		said = home.read()
		assert said["administers"] and {"people", "apps"} <= {one["key"] for one in said["glance"]}, said["glance"]
		saved = frappe.get_doc({"doctype": "Report", "report_name": "Open Deals Gulf", "ref_doctype": "Opportunity", "report_type": "Report Builder", "is_standard": "No", "json": "{}"}).insert()
		crm = next(one["module"] for one in reports.where("Report", saved.name)["places"] if one["label"] == "OneCRM")
		reports.place("Report", saved.name, crm, 1)
		assert reports.where("Report", saved.name) | {"places": None} == {"module": crm, "everybody": 1, "places": None, "administers": 1}
		assert reports.where("Report", saved.name)
		assert reports.sidebars()
		kept = lists.listed()
		assert set(kept) == set(lists.HOMES), kept
		for module, doctypes in kept.items():
			kinds = lists.kinds(module)
			assert [one["doctype"] for one in kinds] == doctypes, (module, kinds)
			assert all(set(one) == {"doctype", "label", "count", "icon", "counted"} for one in kinds)
		territory = frappe.get_doc({"doctype": "Territory", "territory_name": "Oman"}).insert()
		assert territory.parent_territory, "a tree's new value goes under its root (lists.place)"
		assert lists.homes()["Territory"] == [
			{"label": "Lists", "route": "/desk/one?center=settings&module=OneCRM&at=lists"},
			{"label": "Territories", "route": "/desk/territory"},
		]
		assert holidays.subdivisions("AE") is not None
		public = holidays.country_holidays("AE", f"{getdate(today()).year + 1}-01-01", f"{getdate(today()).year + 1}-12-31")
		assert public, "no public holidays for the Emirates next year"
		upcoming = holidays.next_year()
		assert frappe.db.exists("Holiday List", upcoming)
		holidays.use(upcoming)
		task = frappe.get_doc({"doctype": "Task", "subject": "Order the W03 sill packers", "project": VILLA}).insert().name
		frappe.delete_doc("Task", task)
		deleted = frappe.db.get_value("Deleted Document", {"deleted_doctype": "Task", "deleted_name": task})
		recycle.restore(deleted)
		assert frappe.db.exists("Task", task)
		frappe.delete_doc("Task", task)
		said = recycle.bulk_restore([frappe.db.get_value("Deleted Document", {"deleted_doctype": "Task", "deleted_name": task, "restored": 0})])
		assert frappe.db.exists("Task", task), said


@check
def the_bin_gives_each_person_back_their_own():
	"""Rania deletes a to-do of hers and finds it in the bin under its title,
	puts it back herself and may not empty it for good. Samir does not see it,
	Layla does, and nobody sees what the system deleted."""
	from onedesk.one import recycle

	with as_user("rania@one.test"):
		todo = frappe.get_doc({"doctype": "ToDo", "description": "Call Gulf Glass about the cracked panel", "allocated_to": "rania@one.test"}).insert()
		frappe.delete_doc("ToDo", todo.name)
	frappe.db.before_commit.run()
	deleted = frappe.db.get_value("Deleted Document", {"deleted_doctype": "ToDo", "deleted_name": todo.name})
	assert "Call Gulf Glass" in (frappe.db.get_value("Deleted Document", deleted, "one_title") or ""), frappe.db.get_value("Deleted Document", deleted, ["one_title", "deleted_name"])
	frappe.set_user("Administrator")
	housekeeping = frappe.get_doc({"doctype": "ToDo", "description": "Old reminder", "allocated_to": OWNER}).insert()
	frappe.delete_doc("ToDo", housekeeping.name)
	swept = frappe.db.get_value("Deleted Document", {"deleted_doctype": "ToDo", "deleted_name": housekeeping.name})
	with as_user("samir@one.test"):
		assert deleted not in frappe.get_list("Deleted Document", pluck="name")
		try:
			recycle.restore(deleted)
			raise AssertionError("Samir put back Rania's to-do")
		except frappe.PermissionError:
			pass
	with as_user(OWNER):
		seen = frappe.get_list("Deleted Document", pluck="name", limit_page_length=0)
		assert deleted in seen and swept not in seen
	with as_user("rania@one.test"):
		assert deleted in frappe.get_list("Deleted Document", pluck="name", limit_page_length=0)
		assert not frappe.has_permission("Deleted Document", "delete", doc=frappe.get_doc("Deleted Document", deleted))
		back = recycle.restore(deleted)
		assert back == todo.name and frappe.db.get_value("ToDo", back, "owner") == "rania@one.test", (back, todo.name)


@check
def webhooks_and_the_audit_log_are_the_administrators():
	"""Layla sends customers to another system by a webhook: over https to a
	public address only, every record, naming fields alone and none she may
	not read, quickly and a few times at most. When its calls give up she is
	told. She reads who changed a customer, without the fields she may not
	read and without what the system did, and changes none of it. Omar sees
	no webhook and no change."""
	from onedesk.one import audit, webhooks

	def hook(**said):
		return frappe.get_doc({
			"doctype": "Webhook", "__newname": frappe.generate_hash(length=8), "webhook_doctype": "Customer", "webhook_docevent": "on_update",
			"request_url": "https://example.com/hook", "request_structure": "JSON",
			"webhook_json": '{"name": "{{ doc.name }}"}', **said,
		})

	def refused(doc):
		try:
			doc.insert()
		except (frappe.ValidationError, frappe.PermissionError):
			return True
		return False

	with as_user(OWNER):
		made = hook(is_dynamic_url=1, timeout=300, max_retries=50).insert()
		assert (made.is_dynamic_url, made.timeout, made.max_retries) == (0, webhooks.LONGEST, webhooks.TRIES)
		assert refused(hook(request_url="http://example.com/hook")), "sent in the clear"
		assert refused(hook(request_url="https://127.0.0.1/hook")), "sent inside"
		assert refused(hook(condition="doc.customer_group == 'Commercial'"))
		assert refused(hook(webhook_json='{"who": "{{ frappe.session.user }}"}'))
		assert "allowed_companies" in audit._unseen("Customer")
		assert refused(hook(webhook_json='{"where": "{{ doc.allowed_companies }}"}')), "a field she may not read"
		assert refused(hook(webhook_doctype="DocType"))
		frappe.get_doc({"doctype": "Webhook Request Log", "webhook": made.name, "url": made.request_url, "status": "Exhausted"}).insert(ignore_permissions=True)
		with _Told() as told:
			webhooks.failing()
		assert OWNER in told.to("Webhooks Failing")

		customer = frappe.get_all("Customer", pluck="name", limit=1)[0]
		doc = frappe.get_doc("Customer", customer)
		doc.customer_details = "Pays on the 25th."
		doc.save()
		changes = frappe.get_list("Version", filters={"ref_doctype": "Customer", "docname": customer}, pluck="name")
		assert changes, "her own change"
		assert not frappe.get_list("Version", filters={"owner": ["in", audit.SYSTEM]}, pluck="name", limit=1)
		assert not frappe.has_permission("Version", "write", doc=frappe.get_doc("Version", changes[0]))
		said = audit.seen({"changed": [["allowed_companies", "", "x"], ["customer_details", "", "Pays on the 25th."]]}, "Customer")
		assert [one[0] for one in said["changed"]] == ["customer_details"]
	with as_user("omar@one.test"):
		for doctype in ("Webhook", "Webhook Request Log", "Version"):
			try:
				assert not frappe.get_list(doctype, pluck="name", limit=1), doctype
			except frappe.PermissionError:
				pass


@check
def an_announcement_is_the_administrators_and_reaches_everybody_once():
	"""Rania's notes stay her own: she may not post one for everybody. Layla
	posts one shown on sign-in, everybody but her is told once, and it is
	waiting for Rania when she next opens One. Nobody signed out sees it."""
	from frappe.desk.doctype.note.note import UNSEEN_NOTES_KEY

	from onedesk.one import announcements

	with as_user("rania@one.test"):
		checklist = frappe.get_doc({"doctype": "Note", "title": "My site checklist", "content": "Sealant, shims, level."}).insert()
		for said in ({"notify_on_login": 1}, {"public": 1}):
			try:
				mine = frappe.get_doc({"doctype": "Note", "title": "To everybody", "content": "Hello", **said}).insert()
			except frappe.ValidationError:
				continue
			assert not frappe.db.get_value("Note", mine.name, "public") and not frappe.db.get_value("Note", mine.name, "notify_on_login"), "Rania posted an announcement"
	with as_user(OWNER), _Told() as told:
		note = frappe.get_doc({
			"doctype": "Note", "title": "Office closed on Thursday", "content": "The office is closed for the holiday.",
			"notify_on_login": 1, "expire_notification_on": add_days(today(), 7),
		}).insert()
		assert note.public, "shown on sign-in is everybody's"
		note.content = "The office is closed on Thursday for the holiday."
		note.save()
	assert [name for name, _users in told.said].count("Announcement") == 1, told.said
	assert "rania@one.test" in told.to("Announcement") and OWNER not in told.to("Announcement")
	with as_user("rania@one.test"):
		frappe.cache.delete_value(f"{UNSEEN_NOTES_KEY}rania@one.test")
		booted = frappe._dict()
		announcements.boot(booted)
		assert note.name in {one.get("name") for one in booted.notes}, booted.notes
		assert note.name in {one["name"] for one in booted.one_announcements["running"]}, "it runs along her top bar"
		assert not booted.one_announcements["folded"]
		assert checklist.name not in {one["name"] for one in announcements.current()["running"]}, "her own note is not on the bar"
		announcements.hide()
		said = announcements.current()
		assert said["folded"] and note.name in {one["name"] for one in said["running"]}, "she folded it, and it is still there"
		announcements.show()
		assert not announcements.current()["folded"], "she opened it again"
	frappe.db.set_value("Note", note.name, "expire_notification_on", add_days(today(), -1))
	with as_user("rania@one.test"):
		assert note.name not in {one["name"] for one in announcements.current()["running"]}, "an expired one leaves the bar"
	frappe.set_user("Guest")
	booted = frappe._dict()
	announcements.boot(booted)
	assert "notes" not in booted


@check
def push_reaches_a_persons_own_browsers():
	"""Rania turns push on in her browser and gets a test push there, then
	turns it off. A push service One does not send to is refused, and the
	service worker is served to anybody. Her sessions elsewhere are signed
	out from her Sign-in page, and a new password set from a reset link
	tells her it changed. The push service is not called."""
	from unittest import mock

	from onedesk.one import push
	from onedesk.account_center import signin

	endpoint = "https://fcm.googleapis.com/fcm/send/demo-rania"
	with as_user("rania@one.test"):
		assert push.devices()["key"]
		push.register(endpoint, "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM", "tBHItJI5svbpez7KI4CCXg", "Rania's laptop")
		assert [one.label for one in push.devices()["devices"]] == ["Rania's laptop"]
		with mock.patch("pywebpush.webpush") as sent:
			push.test()
		assert sent.called
		push.forget(endpoint=endpoint)
		assert not push.devices()["devices"]
		try:
			push.register("https://push.example.com/x", "a", "b")
			raise AssertionError("a push service One does not send to was kept")
		except frappe.ValidationError:
			pass
		assert signin.sign_out("no such session") == 0
	frappe.set_user("Guest")
	assert b"addEventListener" in push.worker().get_data()
	with as_user("rania@one.test"), mock.patch("onedesk.one.tell.password_changed") as told:
		_asked()
		with mock.patch("frappe.core.doctype.user.user.update_password", return_value="/desk"):
			signin.update_password("A-new-long-passphrase-2026", old_password="the old one")
			assert not told.called
			signin.update_password("Another-long-passphrase-2026", old_password="A-new-long-passphrase-2026")
		told.assert_called_once_with("rania@one.test")


@check
def one_atlas_knows_who_may_open_what():
	"""docs/atlas-site.json is this site's: what it has and who may read each record type,
	report and page, every grant of One's applied, which docs/ATLAS.md says
	and tests/guards/test_atlas.py holds. What it keeps is the demo's as
	built, which a site in use only adds to: its scheduler logs, the links
	its files make."""
	import json
	import os

	from onedesk.one import reach

	path = os.path.join(frappe.get_app_path("onedesk"), "..", "docs", "atlas-site.json")
	with open(path) as f:
		kept = json.load(f)
	now = reach.atlas()
	built = set(kept.pop("kept"))
	assert built <= set(now.pop("kept")), "run python scripts/atlas.py --site"
	assert now == kept, "run python scripts/atlas.py --site"
	from frappe.translate import get_all_translations

	frappe.clear_cache()
	assert get_all_translations("en").get("ERPNext Settings") == "Settings"
	assert "ERPNext" not in get_all_translations("de").get("ERPNext User ID", "ERPNext")


@check
def work_and_mail_tell_what_the_second_pass_found():
	"""Samir's completed task reopened by Rania reaches Samir, and cancelled
	reaches him too; a project put back to Open reaches its people; a member
	taken off hears it; a comment on a project reaches its manager; a
	milestone a day late reaches the manager; mail frappe gave up sending
	reaches whoever sent it; a mailbox given to somebody reaches them; a Remind
	Me reaches whoever set it."""
	from unittest.mock import patch

	from onedesk.one_mail import tell as mail
	from onedesk.one_project import tell as projects

	told = []

	def heard(name, users, **said):
		told.append((name, [users] if isinstance(users, str) else list(users), said))

	def said(name):
		found = [one for one in told if one[0] == name]
		assert found, (name, [one[0] for one in told])
		return found[-1]

	with patch("onedesk.one.notify.notify", side_effect=heard):
		task = frappe.get_doc("Task", frappe.db.get_value("Task", {"status": "Completed", "owner": "samir@one.test"}))
		with as_user("rania@one.test"):
			task.status = "Open"
			task.save(ignore_permissions=True)
			assert "samir@one.test" in said("Task Reopened")[1]
			task.status = "Cancelled"
			task.save(ignore_permissions=True)
		assert "samir@one.test" in said("Task Cancelled")[1]

		project = frappe.get_doc("Project", frappe.db.get_value("Project", {"status": "Open", "one_manager": "samir@one.test"}))
		project.append("users", {"user": "rania@one.test"})
		project.save(ignore_permissions=True)
		with as_user(OWNER):
			project.status = "On hold"
			project.save(ignore_permissions=True)
			project.status = "Open"
			project.save(ignore_permissions=True)
			assert "samir@one.test" in said("Project Resumed")[1]
			project.users = [row for row in project.users if row.user != "rania@one.test"]
			project.save(ignore_permissions=True)
		assert said("Removed from Project")[1] == ["rania@one.test"]

		with as_user("rania@one.test"):
			frappe.get_doc({"doctype": "Comment", "comment_type": "Comment", "reference_doctype": "Project", "reference_name": project.name, "content": "Glass arrives Monday.", "comment_email": "rania@one.test"}).insert(ignore_permissions=True)
		assert said("Comment on Project")[1] == ["samir@one.test"]

		milestone = frappe.get_doc({"doctype": "Task", "subject": "Frames installed", "project": project.name, "is_milestone": 1, "exp_end_date": add_days(today(), -1)})
		milestone.flags.ignore_validate = True
		milestone.insert(ignore_permissions=True, ignore_mandatory=True)
		projects.milestones_late()
		assert said("Milestone Late")[2]["milestone"] == "Frames installed"

		sent = frappe.get_doc({"doctype": "Communication", "communication_type": "Communication", "communication_medium": "Email", "sent_or_received": "Sent", "subject": "Your quote", "recipients": "buyer@example.com", "content": "Attached."})
		sent.insert(ignore_permissions=True)
		frappe.db.set_value("Communication", sent.name, {"delivery_status": "Error", "owner": "samir@one.test"})
		mail.not_sent()
		assert said("Mail Not Sent")[1] == ["samir@one.test"]

		mail.mailbox_shared("Sales", ["rania@one.test"])
		assert said("Mailbox Shared With You")[1] == ["rania@one.test"]

		with as_user("samir@one.test"):
			reminder = frappe.get_doc({"doctype": "Reminder", "user": "samir@one.test", "remind_at": frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=5), "description": "Call the glazier", "reminder_doctype": "Project", "reminder_docname": project.name}).insert(ignore_permissions=True)
		reminder.send_reminder()
		_name, users, values = said("Reminder")
		assert users == ["samir@one.test"] and values["said"] == "Call the glazier", values


@check
def the_workspace_tells_what_the_second_pass_found():
	"""An administrator taken away and the sign-in rules changed reach every
	other administrator; a file refused for room reaches them once a day; a
	record moved on from an approval step reaches whoever made it and whoever
	sent it there; an agreement at a new revision reaches the administrators
	once; automations that failed yesterday reach them in the morning."""
	import copy
	from unittest.mock import patch

	from onedesk.one import control, tell
	from onedesk.one.people import told_of_access
	from onedesk.trust_center import gate
	from onedesk.one_studio import approvals

	told = []

	def heard(name, users, **said):
		told.append((name, [users] if isinstance(users, str) else list(users), said))

	def said(name):
		found = [one for one in told if one[0] == name]
		assert found, (name, [one[0] for one in told])
		return found[-1]

	with patch("onedesk.one.notify.notify", side_effect=heard):
		with as_user(OWNER):
			told_of_access(frappe.get_doc("User", "mariam@one.test"), {"Workspace Administrator"}, set())
		assert OWNER not in said("Administrator Removed")[1]

		with as_user(OWNER):
			control.save("general", {"allow_consecutive_login_attempts": 7})
		assert "allow_consecutive_login_attempts" not in str(said("Sign-in Rules Changed")[2]["what"]), said("Sign-in Rules Changed")

		frappe.cache.delete_value("one_cloud_full_told")
		tell.storage_full()
		tell.storage_full()
		assert len([one for one in told if one[0] == "Storage Full"]) == 1

		task = frappe.get_doc("Task", frappe.db.get_value("Task", {"owner": "samir@one.test", "status": "Open"}))
		before = copy.deepcopy(task)
		before.status, task.status = "Open", "Working"
		task._doc_before_save = before
		frappe.get_doc({"doctype": "Workflow Action", "reference_doctype": "Task", "reference_name": task.name, "status": "Completed", "completed_by": "mariam@one.test", "workflow_state": "Working"}).insert(ignore_permissions=True)
		frappe.db.set_value("Workflow Action", {"reference_name": task.name}, "owner", "rania@one.test")
		with as_user("mariam@one.test"), patch("frappe.model.workflow.get_workflow_name", return_value="Task Approval"), patch("frappe.get_cached_value", return_value="status"):
			approvals.answered(task)
		_name, users, values = said("Approval Answered")
		assert users == ["rania@one.test", "samir@one.test"] and str(values["state"]) == "Working", (users, values)

		key = gate.keys_for(gate.WORKSPACE)[0]
		frappe.db.set_default(f"trust_center_told_workspace_{key}", None)
		with patch.object(gate, "_accepted", return_value="0.abc"):
			gate.told_of_changes()
			gate.told_of_changes()
		assert len([one for one in told if one[0] == "Agreements Changed"]) == 1

		run = frappe.get_doc({"doctype": "Automation Run", "automation_title": "Chase overdue invoices", "status": "Failed"}).insert(ignore_permissions=True, ignore_links=True, ignore_mandatory=True)
		frappe.db.set_value("Automation Run", run.name, "creation", add_days(now_datetime(), -1))
		tell.automations_failing()
		assert "Chase overdue invoices (1)" in said("Automations Failing")[2]["automations"]

		from onedesk.one_admin import home
		from onedesk.one_admin import tell as admin

		slow = [{"name": "PJ-X", "title": "Building Sahara is taking hours", "why": "At: Making the site"}]
		filling = [{"title": "f1-dubai is filling up", "why": "41 of 50 workspaces", "badge": "Filling Up"}]
		frappe.db.set_default("one_admin_filling_f1-dubai is filling up", None)
		with patch("onedesk.one_admin.site.is_admin", return_value=True), patch.object(home, "_slow_builds", return_value=slow), patch.object(home, "_filling", return_value=filling), patch.object(admin, "operators", return_value=["wsadmin@one.test"]), patch("frappe.sendmail"):
			admin.builds_slow()
			admin.servers_filling()
			admin.servers_filling()
		assert said("Build Slow")[2]["title"] == "Building Sahara is taking hours"
		assert len([one for one in told if one[0] == "Server Filling Up"]) == 1


@check
def sales_books_and_stock_tell_what_waits_on_somebody():
	"""Layla makes Samir the owner of a lead, and Samir is told; a lead nobody
	owns reaches sales; a quotation three days from its last day reaches
	whoever made it; an invoice gone overdue yesterday reaches whoever made
	it; bills due this week reach accounts; a payment made through a payment
	link is told; Karim's request to buy reaches purchasing; an order not
	delivered by yesterday reaches whoever made it."""
	from unittest.mock import patch

	from onedesk.one_book import tell as books
	from onedesk.one_crm import tell as crm
	from onedesk.one_inventory import tell as stock

	told = []

	def heard(name, users, **said):
		told.append((name, [users] if isinstance(users, str) else list(users), said))

	def said(name, record=None):
		found = [one for one in told if one[0] == name and (not record or one[2].get("record") == record)]
		assert found, (name, record, [one[0] for one in told])
		return found[-1]

	with patch("onedesk.one.notify.notify", side_effect=heard):
		lead = frappe.get_doc("Lead", frappe.db.get_value("Lead", {"lead_owner": ["!=", "samir@one.test"]}))
		with as_user("wsadmin@one.test"):
			lead.lead_owner = "samir@one.test"
			lead.save()
		assert said("Given to You", ("Lead", lead.name))[1] == ["samir@one.test"]

		with as_user("wsadmin@one.test"):
			new = frappe.get_doc({"doctype": "Lead", "lead_name": "Hana Ito", "email_id": "hana.ito@example.com", "lead_owner": ""})
			new.insert()
		if not new.lead_owner:
			assert "samir@one.test" in said("New Lead Waiting", ("Lead", new.name))[1]

		base = frappe.get_doc("Quotation", frappe.db.get_value("Quotation", {"docstatus": 1, "status": "Open"}))
		quote = frappe.copy_doc(base)
		quote.transaction_date, quote.valid_till, quote.payment_schedule, quote.lost_reasons = today(), add_days(today(), 3), [], []
		for row in quote.items:
			row.ordered_qty = 0
		quote.insert(ignore_permissions=True)
		quote.submit()
		crm.running_out()
		assert said("Quotation Running Out", ("Quotation", quote.name))[1], told

		invoice = frappe.db.get_value("Sales Invoice", {"docstatus": 1, "outstanding_amount": [">", 0], "is_return": 0})
		frappe.db.set_value("Sales Invoice", invoice, "due_date", add_days(today(), -1))
		books.overdue()
		assert said("Invoice Overdue", ("Sales Invoice", invoice))[1]

		bill = frappe.db.get_value("Purchase Invoice", {"docstatus": 1, "outstanding_amount": [">", 0]})
		if bill:
			frappe.db.set_value("Purchase Invoice", bill, "due_date", add_days(today(), 2))
			books.bills_due()
			assert said("Bills Due This Week")[2]["count"] >= 1

		paid = frappe._dict(
			payment_type="Receive", party_type="Customer", party=frappe.db.get_value("Sales Invoice", invoice, "customer"), party_name="", paid_from_account_currency="AED",
			references=[frappe._dict(payment_request="ACC-PRQ-1", reference_doctype="Sales Invoice", reference_name=invoice, allocated_amount=100)],
		)
		books.paid_online(paid)
		assert said("Paid Online", ("Sales Invoice", invoice))[2]["invoice"] == invoice

		item = frappe.db.get_value("Item", {"is_stock_item": 1, "disabled": 0})
		with as_user("karim@one.test"):
			asked = frappe.get_doc(
				{"doctype": "Material Request", "material_request_type": "Purchase", "schedule_date": add_days(today(), 7), "items": [{"item_code": item, "qty": 2, "schedule_date": add_days(today(), 7), "warehouse": frappe.db.get_value("Warehouse", {"is_group": 0, "company": COMPANY})}]}
			).insert()
			asked.submit()
		_name, users, values = said("Material Request Asked", ("Material Request", asked.name))
		assert "karim@one.test" not in users and values["who"] == "Karim Mansour", values

		order = frappe.db.get_value("Sales Order", {"docstatus": 1, "status": ["in", ["To Deliver and Bill", "To Deliver"]]})
		if order:
			frappe.db.set_value("Sales Order", order, "delivery_date", add_days(today(), -1))
			stock.deliveries_late()
			assert said("Delivery Late", ("Sales Order", order))[1]


@check
def sales_books_and_stock_tell_what_the_second_pass_found():
	"""Karim asks the stores to move glass and they are told, and when Samir
	stops it Karim is told; a request moved in full reaches whoever asked;
	reordering that failed reaches the stock and buying managers; mail in on
	Omar's lead reaches Omar; a contract two weeks from its end reaches whoever
	made it; a repeat frappe switched off reaches whoever set it up."""
	from types import SimpleNamespace
	from unittest.mock import patch

	from onedesk.one import tell as one
	from onedesk.one_crm import tell as crm
	from onedesk.one_inventory import tell as stock

	told = []

	def heard(name, users, **said):
		told.append((name, [users] if isinstance(users, str) else list(users), said))

	def said(name):
		found = [one for one in told if one[0] == name]
		assert found, (name, [one[0] for one in told])
		return found[-1]

	with patch("onedesk.one.notify.notify", side_effect=heard):
		request = frappe.copy_doc(frappe.get_doc("Material Request", frappe.db.get_value("Material Request", {"material_request_type": "Purchase", "docstatus": 1})))
		request.material_request_type = "Material Transfer"
		for row in request.items:
			row.reorder_level = None
		other = frappe.db.get_value("Warehouse", {"is_group": 0, "company": request.company, "name": ["!=", request.items[0].warehouse]})
		for row in request.items:
			row.from_warehouse = other
		with as_user("karim@one.test"):
			request.insert(ignore_permissions=True, ignore_mandatory=True)
			request.submit()
		_name, users, values = said("Stock Asked")
		assert "karim@one.test" not in users and users and str(values["kind"]) == "Material Transfer", (users, values)
		with as_user("samir@one.test"):
			stock.update_status(request.name, "Stopped")
		assert said("Material Request Stopped")[1] == ["karim@one.test"]

		frappe.db.set_value("Material Request", request.name, "status", "Transferred")
		with as_user("samir@one.test"):
			stock.moved(SimpleNamespace(items=[frappe._dict(material_request=request.name)]))
		assert said("Material Request Done")[1] == ["karim@one.test"]

		frappe.get_doc({"doctype": "Error Log", "method": "Unable to create material request", "error": "No supplier"}).insert(ignore_permissions=True)
		stock.reorder_failed()
		assert said("Reordering Failed")[2]["count"] >= 1

		lead = frappe.db.get_value("Lead", {"lead_owner": "omar@one.test"})
		frappe.get_doc({"doctype": "Communication", "communication_type": "Communication", "communication_medium": "Email", "sent_or_received": "Received", "sender": "buyer@example.com", "sender_full_name": "Hana Buyer", "subject": "Re: your quote", "content": "Can you do Thursday?", "reference_doctype": "Lead", "reference_name": lead}).insert(ignore_permissions=True)
		_name, users, values = said("They Replied")
		assert users == ["omar@one.test"] and values["who"] == "Hana Buyer", values

		contract = frappe.get_doc("Contract", frappe.db.get_value("Contract", {}))
		frappe.db.set_value("Contract", contract.name, {"status": "Active", "end_date": add_days(today(), 14), "docstatus": 1 if contract.docstatus == 1 else 0})
		crm.contracts_ending()
		assert said("Contract Expiring")[1], said("Contract Expiring")

		repeat = frappe.db.get_value("Auto Repeat", {}, ["name", "owner"], as_dict=True)
		frappe.db.set_value("Auto Repeat", repeat.name, "disabled", 1)
		frappe.get_doc({"doctype": "Error Log", "method": "Auto repeat failed", "reference_doctype": "Auto Repeat", "reference_name": repeat.name, "error": "x"}).insert(ignore_permissions=True)
		one.repeats_failed()
		assert repeat.owner in said("Repeat Failed")[1] or said("Repeat Failed")[1], said("Repeat Failed")


@check
def the_workspace_tells_what_it_promised_to():
	"""Credits that run out are told to the administrators, always mailed; a
	sign-in from a new device is told to the person and their first is not;
	Fix With OneAI's result is kept on the bell; a document OneAI could not
	read is told to whoever it reads for; an approval offers "Approve or
	Reject"; the owner of a workspace whose payment failed is mailed."""
	from types import SimpleNamespace
	from unittest.mock import patch

	from onedesk.one import account, tell
	from onedesk.account_center import signin
	from onedesk.one_admin import tell as admin
	from onedesk.one_ai.reading import tell as intake
	from onedesk.one_studio import tell as studio

	told, mailed = [], []

	def heard(name, users, **said):
		told.append((name, [users] if isinstance(users, str) else list(users), said))

	def sent(name, to, **said):
		mailed.append((name, to, said))

	with patch("onedesk.one.notify.notify", side_effect=heard), patch("onedesk.one.notify.mail", side_effect=sent):
		with patch.object(account, "_administrators", return_value=["wsadmin@one.test"]):
			account._tell({"last_heard": 1, "credits_balance": 40}, frappe._dict(credits_balance=0, credits_month=0, domains=[], storage_limit=0, database_limit=0))
		assert ("Credits Ran Out", ["wsadmin@one.test"]) in [(one[0], one[1]) for one in told], told

		frappe.defaults.clear_user_default("one_devices", "rania@one.test")
		request = SimpleNamespace(headers={"User-Agent": "Mozilla/5.0 (Macintosh; Mac OS X) Chrome/120"})
		with patch.object(frappe, "request", request, create=True), patch.object(frappe.local, "request", request, create=True):
			signin.arrived(SimpleNamespace(user="rania@one.test"))
			assert not [one for one in told if one[0] == "New Sign-in"], "the first sign-in is where they start"
			request.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0) Firefox/121"
			signin.arrived(SimpleNamespace(user="rania@one.test"))
		assert [one[1] for one in told if one[0] == "New Sign-in"] == [["rania@one.test"]], told

		studio.extension_fixed("wsadmin@one.test", "EXT-1", "Late fee", "Fixed the date check.")
		assert told[-1][0] == "Extension Fixed" and told[-1][2]["said"] == "Fixed the date check."

		intake.couldnt_read(frappe._dict(name="RD-1", title="Invoice 44", on_behalf_of="karim@one.test"), waiting=True)
		assert told[-1][0] == "Couldn't Read" and "credits" in told[-1][2]["why"]

		assert tell._or(["Approve", "Reject"]) == "Approve or Reject"
		assert tell._or(["Approve", "Reject", "Send Back"]) == "Approve, Reject or Send Back"

		with patch("onedesk.one_admin.site.is_admin", return_value=True):
			admin.owner(frappe._dict(name="T-1", workspace_name="Acme", account="owner@acme.example"), "Overdue", "Live")
			assert mailed and mailed[-1][0] == "Payment Failed" and mailed[-1][1] == "owner@acme.example", mailed


@check
def starting_again_keeps_the_setup_and_is_the_administrators():
	"""Start Again deletes transactions, not the customers, accounts, people
	or settings they were made with; and only an administrator may start it.
	The plan is drawn and thrown away: submitting it would delete the demo."""
	from onedesk.one import start_again

	with as_user("rania@one.test"):
		try:
			start_again.start()
			raise AssertionError("somebody who is not an administrator started again")
		except frappe.PermissionError:
			pass
	with as_user("Administrator"):
		plan = start_again.planned(COMPANY)
	try:
		going = {one.doctype_name for one in plan.doctypes_to_delete if one.document_count}
		assert {"Sales Invoice", "Stock Entry", "Lead"} <= going, going
		kept = {"Customer", "Supplier", "Account", "Employee", "Item", "UAE VAT Settings", "Tax Rule", "Pricing Rule"}
		assert not kept & going, kept & going
	finally:
		frappe.delete_doc(start_again.DOCTYPE, plan.name, force=True, ignore_permissions=True)


@check
def whats_new_says_each_version_once():
	"""Nadia sees OneMail's version marked unseen until she opens What's New,
	which lists its versions newest first, written for her, and then marks
	them seen (one/versions.py). Its pictures come from R2 by their hash, and
	the workspace serves the same picture when R2 can't, but nothing outside
	a module's docs (one/media.py)."""
	from onedesk.one import media, ready, versions

	with as_user("nadia@one.test"):
		frappe.defaults.set_user_default(versions.SEEN.format("one_mail"), "")
		said = versions.for_boot()["OneMail"]
		assert said["version"] == ready.current("OneMail") and said["unseen"] == 1 and "off" not in said, said
		listed = versions.whats_new("OneMail")["versions"]
		assert listed[0]["version"] == ready.current("OneMail") and listed[0]["new"], listed[0]
		html = listed[-1]["html"]
		assert f'src="{media.base()}/docs/' in html and "data-here=" in html, html[:300]
		assert versions.for_boot()["OneMail"]["unseen"] == 0
		assert not versions.whats_new("OneMail")["versions"][0]["new"]
		from html import unescape
		from urllib.parse import parse_qs, urlsplit

		here = parse_qs(urlsplit(unescape(html.split('data-here="', 1)[1].split('"', 1)[0])).query)
		media.picture(here["module"][0], here["path"][0])
		assert frappe.local.response["content_type"].startswith("image/")
		try:
			media.picture("OneMail", "../hooks.py")
			raise AssertionError("a path outside the docs is refused")
		except frappe.DoesNotExistError:
			pass


@check
def help_shows_every_page_in_order():
	"""OneMail's Help gives Nadia its pages in the order ready.MODULES lists
	them, each with its icon and a heading, and every page a version reads
	more in is one of them (one/versions.py help_pages)."""
	from onedesk.one import ready, versions

	with as_user("nadia@one.test"):
		said = versions.help_pages("OneMail")
		assert said["version"] == ready.current("OneMail"), said["version"]
		pages = said["pages"]
		assert [one["id"] for one in pages] == [page for page, _icon in ready.MODULES["OneMail"]["help"]]
		assert all(one["icon"] and one["title"] and one["html"].strip() for one in pages), pages[0]
		ids = {one["id"] for one in pages}
		for one in versions.whats_new("OneMail")["versions"]:
			assert {page["id"] for page in one["docs"]} <= ids, one["docs"]
		# Who Can Do What shows what OneMail's roles ship with, from its
		# access.py (one/rights.py defaults_table).
		roles = next(one["html"] for one in pages if one["id"] == "who-can-do-what")
		assert "{roles}" not in roles and "Every Mailbox" in roles and "Ask for Approval" in roles, roles[:200]
	from onedesk.one.notify import declared

	assert declared()["Mail Not Sent"]["email"] is False and declared()["Attachments Not Saved"]["from_one"] is True
	assert not declared()["Covering Mail"].get("from_one")


@check
def help_is_only_for_apps_that_are_on():
	"""HelpCenter and Ctrl+K list the Help of the apps that are on, by
	title, {one_cloud}'s and {one_studio}'s among them; an app the
	workspace turns off is marked off and left out (one/versions.py
	for_boot)."""
	import json

	from onedesk.one import apps, registry, versions

	cloud, studio, mail = registry.name("one_cloud"), registry.name("one_studio"), registry.name("one_mail")
	hidden = frappe.db.get_default(apps.KEY)
	try:
		frappe.db.set_default(apps.KEY, "[]")
		with as_user(OWNER):
			said = versions.for_boot()
			for module in (cloud, studio):
				assert module in said and not said[module].get("off"), module
				assert [page for page, _title in said[module]["pages"]][0] == "overview" and all(title for _page, title in said[module]["pages"]), said[module]["pages"]
		frappe.db.set_default(apps.KEY, json.dumps([registry.get("one_mail").sidebar]))
		with as_user(OWNER):
			assert versions.for_boot()[mail].get("off") == 1
			assert not versions.for_boot()[cloud].get("off")
	finally:
		frappe.db.set_default(apps.KEY, hidden or "[]")


@check
def the_update_window_is_oneadmins_and_an_administrators_to_change():
	"""UpdateCenter's This Workspace (one/update_window.py): everybody reads
	when the next update is and the window, from the account; the owner
	changes the window and updates now through OneAdmin, told plainly when
	nothing waits; Nadia may not."""
	from unittest import mock

	from onedesk.one import update_window

	fields = {"update_at": None, "update_weekday": 0, "update_hour": 9, "update_moving": 0, "update_held_until": None}
	assert update_window.plainly({}) == {"at": None, "weekday": 5, "hour": 1, "moving": 0, "held_until": None}, "OneAdmin's Saturday 01:00 until it says"
	assert update_window.plainly(fields)["weekday"] == 0 and update_window.plainly(fields)["hour"] == 9
	with (
		mock.patch("onedesk.one.account.configured", return_value=True),
		mock.patch("onedesk.one.account.refresh"),
		mock.patch("onedesk.one.account.ask", return_value={"waiting": False}) as asked,
	):
		with as_user("nadia@one.test"):
			said = update_window.state()
			assert said["linked"] and not said["may"], said
			for refused in (lambda: update_window.set_window(0, 9), update_window.update_now):
				try:
					refused()
					raise AssertionError("Nadia changed the update")
				except frappe.PermissionError:
					pass
		with as_user(OWNER):
			assert update_window.state()["may"]
			update_window.set_window(0, 9)
			assert asked.call_args.args == ("onedesk.one_admin.proxy.update_window",) and asked.call_args.kwargs == {"weekday": 0, "hour": 9}
			assert update_window.update_now()["waiting"] == 0, "no newer release, so nothing happens"
			try:
				update_window.set_window(7, 9)
				raise AssertionError("an eighth day was taken")
			except frappe.ValidationError:
				pass


@check
def training_copies_are_an_administrators_to_make_and_open_on_the_fields_company():
	"""AccountCenter's Training Copies (one/copies.py), with OneAdmin's
	answers faked: Nadia may not open it or make a copy; the owner sees why
	none can be made while Training Copies is off, makes one from the demo
	for the clinic through proxy.copies_start, is told OneAdmin's refusal in
	words, and a copy from the demo opens on the clinic's company."""
	from unittest import mock

	from onedesk.account_center import center
	from onedesk.one import copies
	from onedesk.one_demo import clinic_field

	listed = [{"name": "WS-1", "kind": "demo", "field": "clinic", "status": "Running", "link": "https://s-1.example.com", "expires_on": "2026-11-20 09:00:00"}]

	def oneadmin(endpoint, **said):
		return {"onedesk.one_admin.proxy.copies_listed": listed, copies.START: {**listed[0], "status": "Starting"}}.get(endpoint, {"ok": True})

	with (
		mock.patch("onedesk.one.account.configured", return_value=True),
		mock.patch("onedesk.trust_center.services.offered", return_value=True),
		mock.patch("onedesk.one.account.ask", side_effect=oneadmin) as asked,
	):
		with as_user("nadia@one.test"):
			for refused in (lambda: center.load("copies"), lambda: copies.start("demo", "7 Days", "clinic")):
				try:
					refused()
					raise AssertionError("Nadia reached Training Copies")
				except frappe.PermissionError:
					pass
		with as_user(OWNER), mock.patch("onedesk.trust_center.services.on", return_value=False):
			said = center.load("copies")
			assert said["why_not"] == "agreed" and said["copies"] == listed, said
			try:
				copies.start("demo", "7 Days", "clinic")
				raise AssertionError("a copy was made with Training Copies off")
			except frappe.ValidationError:
				pass
		asked.reset_mock()
		with as_user(OWNER), mock.patch("onedesk.trust_center.services.on", return_value=True):
			assert center.load("copies")["why_not"] is None
			copies.start("demo", "7 Days", "clinic")
			assert asked.call_args.args == (copies.START,), asked.call_args
			assert asked.call_args.kwargs == {"kind": "demo", "lasts": "7 Days", "field": "clinic", "by": OWNER}, asked.call_args
			with mock.patch("onedesk.one.account.ask", return_value={"refused": "many", "most": 3}):
				try:
					copies.start("data", "1 Day")
					raise AssertionError("OneAdmin's refusal was not said")
				except frappe.ValidationError as raised:
					assert str(raised) == copies.refused("many", 3), raised
			with mock.patch("onedesk.one.account.ask", return_value={"url": "https://s-1.example.com/app?sid=once"}) as opened:
				assert copies.open_copy("WS-1")["url"].startswith("https://s-1.example.com")
				copies.end("WS-1")
				assert [one.args[0] for one in opened.call_args_list] == ["onedesk.one_admin.proxy.copies_sign_in", "onedesk.one_admin.proxy.copies_end"], opened.call_args_list
	was = frappe.defaults.get_global_default("company")
	with mock.patch.object(frappe.db, "commit"):
		try:
			copies.open_on({"one_copy_company": clinic_field.COMPANY})
			assert frappe.defaults.get_global_default("company") == clinic_field.COMPANY
			copies.open_on({"one_copy_company": "No Such Company"})
			assert frappe.defaults.get_global_default("company") == clinic_field.COMPANY, "a company the copy has not made yet waits"
		finally:
			frappe.defaults.set_global_default("company", was)


@check
def setup_steps_are_slides_then_to_dos():
	"""OneMail's setup steps (one/setup_steps.py): Layla, who administers the
	workspace, sees all three and Nadia none; the two with fields would be
	wizard slides, named for the module and step; one given in the wizard is
	saved and done, one left empty stays a to-do, and SetupCenter's Mark as
	Done finishes one."""
	from unittest.mock import patch

	from onedesk.one import setup_center, setup_steps
	from onedesk.one_mail import addresses

	with as_user(OWNER):
		steps = setup_steps.for_boot()["OneMail"]
	assert [one["key"] for one in steps] == ["domains", "private", "templates"], steps
	with as_user("nadia@one.test"):
		assert "OneMail" not in setup_steps.for_boot()
	with patch("frappe.is_setup_complete", return_value=False):
		slides = setup_steps.for_wizard()
	names = [field["fieldname"] for slide in slides for field in slide["fields"]]
	assert names[:2] == ["one_mail_domains_domain", "one_mail_private_allowed"], names
	assert set(names[2:]) == {"one_service_weather", "one_service_google_news", "one_service_gravatar", "one_service_logos", "one_service_web_search", "one_service_training_copies", "one_service_google_fonts"}, names
	assert slides[-1]["name"] == "one_services" and not any(field["default"] for field in slides[-1]["fields"]), "the optional services start off"
	was = frappe.db.get_default(addresses.EXTERNAL)
	flags = {key: frappe.db.get_default(setup_steps.FLAG.format("one_mail", key)) for key in ("private", "templates")}
	try:
		setup_steps.apply({"one_mail_private_allowed": 0, "one_mail_domains_domain": ""})
		assert frappe.db.get_default(addresses.EXTERNAL) == "0"
		with as_user(OWNER):
			said = {one["key"]: one["done"] for one in setup_steps.for_boot()["OneMail"]}
			assert said["private"] == 1 and said["templates"] == 0, said
			left = next(one for one in setup_center.finish("OneMail", "templates")["apps"] if one["app"] == "OneMail")["steps"]
		assert next(one for one in left if one["key"] == "templates")["done"] == 1
	finally:
		frappe.db.set_default(addresses.EXTERNAL, was) if was is not None else frappe.db.set_default(addresses.EXTERNAL, "1")
		for key, value in flags.items():
			frappe.db.set_default(setup_steps.FLAG.format("one_mail", key), value or "")


@check
def setupcenter_lists_each_apps_steps_and_saves_their_forms():
	"""SetupCenter (one/setup_center.py): Layla, who administers the
	workspace, sees every app on with steps, in the rail's order,
	AccountCenter's and OneMail's among them, and a step with fields carries
	the wizard's own fields; Nadia, who may do none, sees none and has no
	row for it; an app turned off leaves it; OneMail's Private Mailboxes
	saved from its form is done and says so."""
	import json

	from onedesk.one import apps, registry, setup_center, setup_steps
	from onedesk.one_mail import addresses

	mail = registry.name("one_mail")
	with as_user(OWNER):
		said = setup_center.load()["apps"]
		assert setup_center.reaches()
	listed = [one["app"] for one in said]
	assert registry.name("account_center") in listed and mail in listed, listed
	steps = {one["key"]: one for one in next(one for one in said if one["app"] == mail)["steps"]}
	assert [field["fieldname"] for field in steps["private"]["fields"]] == ["allowed"] and not steps["templates"]["fields"], steps
	assert next(one for one in said if one["app"] == mail)["center"] == "settings"
	assert next(one for one in said if one["app"] == registry.name("account_center"))["center"] == "account"
	with as_user("nadia@one.test"):
		assert not setup_center.load()["apps"] and not setup_center.reaches()
	was = frappe.db.get_default(addresses.EXTERNAL)
	flag = frappe.db.get_default(setup_steps.FLAG.format("one_mail", "private"))
	hidden = frappe.db.get_default(apps.KEY)
	try:
		frappe.db.set_default(setup_steps.FLAG.format("one_mail", "private"), "")
		with as_user(OWNER):
			after = setup_center.save(mail, "private", {"allowed": 0})["apps"]
		assert frappe.db.get_default(addresses.EXTERNAL) == "0"
		saved = next(one for one in next(one for one in after if one["app"] == mail)["steps"] if one["key"] == "private")
		assert saved["done"] == 1, saved
		frappe.db.set_default(apps.KEY, json.dumps([registry.get("one_mail").sidebar]))
		with as_user(OWNER):
			assert mail not in [one["app"] for one in setup_center.load()["apps"]]
	finally:
		frappe.db.set_default(addresses.EXTERNAL, was if was is not None else "1")
		frappe.db.set_default(setup_steps.FLAG.format("one_mail", "private"), flag or "")
		frappe.db.set_default(apps.KEY, hidden or "[]")


@check
def setupcenter_s_guide_answers_and_fills_a_step_as_a_card():
	"""SetupCenter's setup guide (one/setup_center_agent.py): with
	SetupCenter open, Layla's panel talks to it and Nadia's, who may do no
	step, to Una; it has its own reads and fill_step, never create_record;
	it answers her question with the model faked; asked to fill Private
	Mailboxes it holds no role, so the answers are a card in her
	conversation and nothing changes until she approves it there, and then
	the step is saved and done and cannot be undone from the card."""
	import json
	from unittest import mock

	from onedesk.one import setup_center_agent, setup_steps
	from frappe.permissions import AUTOMATIC_ROLES

	from onedesk.one.registry import agents
	from onedesk.one_ai.agents import levels, talk, users
	from onedesk.one_chat import agents as members
	from onedesk.one_chat import cards
	from onedesk.one_mail import addresses

	mail = "OneMail"
	users.ensure()
	guide = agents.get("setup_center")
	assert guide and guide.roles == () and not set(frappe.get_roles(guide.email)) - set(AUTOMATIC_ROLES), "the guide holds no role"
	assert levels.of("setup_center", "fill_step") == levels.ASK_FIRST and levels.of("setup_center", "about_steps") == levels.DO_IT
	with as_user(OWNER):
		assert members.for_page({"page": "setup", "section": mail}) == "setup_center"
		reads, suggests = talk.tools_of("setup_center")
		named = {fn.__name__ for fn in reads + suggests}
		assert {"about_steps", "about_apps", "how_to", "fill_step"} <= named and not named & {"create_record", "edit_record", "suggest_answer", "ask_agent"}, named
		steps = {(one["app"], one["key"]): one for one in setup_center_agent.about_steps()}
		assert steps[(mail, "private")]["may_fill"] and not steps[(mail, "templates")]["may_fill"], steps
		assert setup_center_agent.about_apps(mail)["help"], "an app's Help"
		model = {"done": True, "credits": 0, "turns": [{"role": "user", "text": "What is Private Mailboxes?"}, {"role": "model", "text": "It lets people connect their own mailbox."}]}
		with mock.patch("onedesk.one_ai.run.turn", return_value=model) as asked:
			out = talk.ask("setup_center", "chat", "What is Private Mailboxes?", [{"role": "user", "text": talk.who("setup_center"), "calls": [], "context": True}])
		assert out["agent"] == "setup_center" and "fill_step" in {one["name"] for one in asked.call_args.args[3]}
	with as_user("nadia@one.test"):
		assert members.for_page({"page": "setup"}) == members.UNA
	was = frappe.db.get_default(addresses.EXTERNAL)
	flag = frappe.db.get_default(setup_steps.FLAG.format("one_mail", "private"))
	frappe.db.savepoint("setup_guide_check")
	try:
		frappe.db.set_default(addresses.EXTERNAL, "1")
		frappe.db.set_default(setup_steps.FLAG.format("one_mail", "private"), "")
		with as_user(OWNER):
			said = setup_center_agent.fill_step(mail, "private", {"allowed": 0, "domain": "elsewhere.example"}, "Only the company's mail.")
			assert said["state"].startswith("Waiting"), said
			row = frappe.get_last_doc("Reading Action", filters={"agent": guide.email, "kind": "Step"})
			assert row.level == "Proposed" and row.on_behalf_of == OWNER and json.loads(row.after) == {"_app": mail, "_step": "private", "allowed": 0}
			assert frappe.db.get_default(addresses.EXTERNAL) == "1", "nothing changes before the card is approved"
			shown = cards.card(row.name)
			assert cards.said(row) and [one["label"] for one in shown["fields"]] == [str(frappe._("People May Connect Their Own Mailboxes"))], shown
			assert frappe.db.exists("Chat Message", {"action": row.name}), "the card is in her conversation with the guide"
			cards.approve(row.name)
			assert frappe.db.get_default(addresses.EXTERNAL) == "0" and frappe.db.get_default(setup_steps.FLAG.format("one_mail", "private")) == "1"
			assert cards.undo(row.name)["undone"] == 0
	finally:
		frappe.db.rollback(save_point="setup_guide_check")
		frappe.db.set_default(addresses.EXTERNAL, was if was is not None else "1")
		frappe.db.set_default(setup_steps.FLAG.format("one_mail", "private"), flag or "")


@check
def tour_runs_once_then_from_help():
	"""OneMail's tours (one/tours.py): one for its mailbox, six steps in the
	reader's language, each at a mark; a reader who hasn't taken it has it in
	the boot, and once taken or closed it doesn't start on its own again."""
	from onedesk.one import tours

	key = tours.SEEN.format("one_mail", "mailbox")
	with as_user("nadia@one.test"):
		was = frappe.defaults.get_user_default(key)
		try:
			frappe.defaults.clear_user_default(key)
			assert "OneMail:mailbox" in tours.unseen()
			said = tours.tour("OneMail")
			assert [one["key"] for one in said] == ["mailbox"] and said[0]["at"] == "onemail-list", said
			steps = said[0]["steps"]
			assert [one["target"] for one in steps][:2] == ["interface-nav", "interface-new"], steps
			assert all(one["title"] and one["text"] for one in steps), steps
			tours.seen("OneMail", "mailbox")
			assert "OneMail:mailbox" not in tours.unseen()
		finally:
			if was != "1":
				frappe.defaults.clear_user_default(key)


@check
def access_center_finds_and_sets_roles():
	"""AccessCenter (one/access_center.py) has OneMail's part, found from its
	access.py: its people with their role, which it changes and puts
	back, and what somebody was given on one mailbox, which it takes away.
	Nobody else may read it."""
	from onedesk.one import access_center, rights

	with as_user("wsadmin@one.test"):
		assert "OneMail" in access_center.modules()
		said = access_center.people("OneMail")
		assert {"User", "Manager"} <= {one["value"] for one in said["levels"]}, said["levels"]
		assert "None" not in {one["value"] for one in said["levels"]}, "everybody uses OneMail"
		nadia = next(one for one in said["people"] if one["user"] == "nadia@one.test")
		was = nadia["level"]
		try:
			access_center.put("OneMail", "nadia@one.test", "Manager")
			assert next(one for one in access_center.people("OneMail")["people"] if one["user"] == "nadia@one.test")["level"] == "Manager"
		finally:
			access_center.put("OneMail", "nadia@one.test", was)
		box = frappe.get_all("Email Account", filters={"email_id": ["like", "%"]}, pluck="name", limit=1)[0]
		had = rights.grants("OneMail", box).get("nadia@one.test")
		try:
			access_center.give("OneMail", box, "nadia@one.test", ["signature"])
			given = [one for one in access_center.records("OneMail")["grants"] if one["user"] == "nadia@one.test" and one["record"] == box]
			assert given and given[0]["given"] == ["signature"], given
			access_center.give("OneMail", box, "nadia@one.test", [])
			assert not [one for one in access_center.records("OneMail")["grants"] if one["user"] == "nadia@one.test" and one["record"] == box]
		finally:
			if had:
				rights.grant("OneMail", box, "nadia@one.test", had)
	with as_user("nadia@one.test"):
		try:
			access_center.people("OneMail")
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody who doesn't administer the workspace read AccessCenter")


@check
def notification_center_sets_yours_and_the_workspace():
	"""NotificationCenter (one/notification_notification_center.py): a reader's own
	choice of email for one of OneMail's types, saved and put back; the
	workspace's setting of a type, set and put back by an administrator and
	refused to anybody else."""
	from onedesk.one import notification_center

	with as_user("nadia@one.test"):
		was = notification_center.yours("OneMail")["email"]
		try:
			notification_center.switch("enable_email_notifications", 0 if was else 1)
			assert notification_center.yours("OneMail")["email"] != was
		finally:
			notification_center.switch("enable_email_notifications", was)
		mine = notification_center.yours("OneMail")["types"]
		one = next(kind for kind in mine if kind["may_email"])
		try:
			notification_center.choose(one["name"], "email", 0 if one["email"] else 1)
			now = next(kind for kind in notification_center.yours("OneMail")["types"] if kind["name"] == one["name"])
			assert now["email"] != one["email"], now
		finally:
			notification_center.choose(one["name"], "email", one["email"])
		try:
			notification_center.set_type(one["name"], "one_allow_push", 0)
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody who doesn't administer the workspace set a notification type")
	with as_user("wsadmin@one.test"):
		types = notification_center.workspace("OneMail")
		assert types and all(kind["app"] == "OneMail" for kind in types), types
		assert all(set(kind) >= {"enabled", "one_allow_email", "one_allow_push"} for kind in types), types
		kind = next(t for t in types if not t["fixed"])
		try:
			notification_center.set_type(kind["name"], "enabled", 0 if kind["enabled"] else 1)
			assert frappe.db.get_value("Notification Type", kind["name"], "enabled") != kind["enabled"]
			try:
				notification_center.set_type(kind["name"], "one_push_default", 1)
			except frappe.ValidationError:
				pass
			else:
				raise AssertionError("an administrator set who starts with a channel on; the module says that")
		finally:
			notification_center.set_type(kind["name"], "enabled", kind["enabled"])


@check
def one_manager_sees_what_anybody_deleted():
	"""One's roles are made from its access.py (rights.settle) and its User
	role is everybody's. Nadia sees only what she deleted herself; made One's
	Manager in AccessCenter, which holds Everyone's Deletions, she sees what
	others deleted too, and still can't empty the bin for good. The demo keeps
	Mariam as One's Manager."""
	from onedesk.one import access_center, recycle

	assert frappe.db.exists("Role", "One User") and frappe.db.exists("Role", "One Manager")
	assert "One User" in frappe.get_roles("nadia@one.test")
	others = frappe.db.get_value(
		"Deleted Document", {"owner": ("not in", ("nadia@one.test", "Administrator", "Guest"))}, "name"
	)
	assert others, "the demo has nothing deleted by anybody but Nadia"
	with as_user("nadia@one.test"):
		assert "nadia@one.test" in (recycle.query() or "") and not recycle._everyone("nadia@one.test")
	assert "One" in access_center.modules() and "AccountCenter" in access_center.modules()
	levels = {one["user"]: one["level"] for one in access_center.people("One")["people"]}
	assert levels.get("mariam@one.test") == "Manager" and levels.get("nadia@one.test") == "User", levels
	access_center.put("One", "nadia@one.test", "Manager")
	try:
		with as_user("nadia@one.test"):
			assert recycle._everyone("nadia@one.test"), "One Manager does not hold Everyone's Deletions"
			doc = frappe.get_doc("Deleted Document", others)
			assert recycle.has_permission(
				doc, "read", "nadia@one.test"
			) or doc.deleted_doctype not in recycle._kinds("nadia@one.test")
			assert not recycle.has_permission(doc, "delete", "nadia@one.test"), (
				"only an administrator empties the bin"
			)
	finally:
		access_center.put("One", "nadia@one.test", "User")
		assert "One User" in frappe.get_roles("nadia@one.test") and "One Manager" not in frappe.get_roles("nadia@one.test")


@check
def the_bin_lists_what_was_deleted_and_puts_it_back():
	"""Nadia deletes a to-do; frappe's Deleted Document list, the Recycle Bin,
	shows it to her and nobody else's, and Restore (recycle.bulk_restore)
	brings it back, marking the row restored."""
	from onedesk.one import recycle

	with as_user("nadia@one.test"):
		note = frappe.get_doc({"doctype": "ToDo", "description": "Bin check: call the glass supplier"}).insert()
		frappe.delete_doc("ToDo", note.name)
		rows = frappe.get_list(
			"Deleted Document",
			filters={"deleted_doctype": "ToDo", "restored": 0},
			fields=["name", "deleted_name", "owner"],
			limit=500,
		)
		row = next((one for one in rows if one.deleted_name == note.name), None)
		assert row, rows
		assert not recycle._everyone("nadia@one.test")
		assert all(one.owner == "nadia@one.test" for one in rows), "Nadia sees somebody else's deletion"
		got = recycle.bulk_restore([row.name])
		assert got["restored"] == [row.name], got
		back = frappe.db.get_value("Deleted Document", row.name, ["restored", "new_name"], as_dict=True)
		assert back.restored and back.new_name, back
		frappe.delete_doc("ToDo", back.new_name)


@check
def announcements_show_now_and_earlier_and_who_saw_them():
	"""Layla posts an announcement with no end: it is given one a week out, so
	it is under Showing Now (Note's list, Show Until after now) for Samir, who
	cannot stop it; Layla stops it and it is under Earlier."""
	from frappe.utils import now_datetime

	from onedesk.one import announcements

	with as_user(OWNER):
		note = frappe.get_doc(
			{"doctype": "Note", "title": "Check: lift out of service", "content": "<p>Use the stairs.</p>", "public": 1}
		).insert()
		assert note.expire_notification_on and not note.notify_on_login, note.as_dict()
	shown = lambda op: frappe.get_list(  # noqa: E731
		"Note", filters={"public": 1, "expire_notification_on": [op, now_datetime()]}, pluck="name"
	)
	with as_user("samir@one.test"):
		assert note.name in shown(">") and note.name not in shown("<=")
		try:
			announcements.stop(note.name)
			raise AssertionError("Samir stopped an announcement")
		except frappe.PermissionError:
			frappe.clear_last_message()
	with as_user(OWNER):
		announcements.stop(note.name)
		assert note.name in shown("<=") and note.name not in shown(">")
		frappe.delete_doc("Note", note.name)


@check
def the_address_book_is_frappes_contacts_and_addresses():
	"""The rail's Contacts and Addresses are frappe's Contact and Address
	lists, and Acme Holdings' billing address and Jordan Blake both belong to
	Acme under Links."""
	rail = {one.label: one for one in frappe.get_all("Sidebar Item", filters={"parent": "One", "parenttype": "Sidebar"}, fields=["label", "link_type", "link_to"])}
	assert (rail["Contacts"].link_type, rail["Contacts"].link_to) == ("DocType", "Contact"), rail["Contacts"]
	assert (rail["Addresses"].link_type, rail["Addresses"].link_to) == ("DocType", "Address"), rail["Addresses"]
	with as_user(OWNER):
		for doctype in ("Address", "Contact"):
			linked = frappe.get_list(
				doctype,
				filters=[["Dynamic Link", "link_doctype", "=", "Customer"], ["Dynamic Link", "link_name", "=", "Acme Holdings"]],
				pluck="name",
			)
			assert linked, doctype


@check
def ones_rail_leaves_out_what_the_reader_cannot_open():
	"""One's rail links the workspace's centres by address, which frappe
	shows to everyone (reach.unopened): Mariam, who administers nothing, has
	AccountCenter and not ControlCenter or AccessCenter; Layla has them all."""
	from frappe.boot import get_module_sidebars

	from onedesk.one import reach

	def rail(user):
		with as_user(user):
			sidebars = get_module_sidebars()
			reach.unopened(sidebars)
			return [one.get("label") for one in sidebars["One"]["items"]]

	mariam, layla = rail("mariam@one.test"), rail(OWNER)
	assert "AccountCenter" in mariam and not {"ControlCenter", "AccessCenter"} & set(mariam), mariam
	assert {"AccountCenter", "ControlCenter", "AccessCenter", "TrustCenter"} <= set(layla), layla


@check
def a_record_with_no_picture_gets_one_drawn_and_keeps_its_own():
	"""A style picked for contacts in One's settings (avatars.save) draws a
	picture for a new contact with none, locally; one with its own picture
	keeps it; changing the style redraws only the drawn one, and None takes
	it off. The workspace's own choice is put back after."""
	from onedesk.one import avatars
	from onedesk.one_mail import faces

	before = frappe.db.get_default(avatars.KEY)
	keys = {one["key"] for one in avatars.styles()}
	assert {"lorelei", "shapes", "initials"} <= keys, sorted(keys)
	assert set(avatars.gallery("Contact")) == keys
	plain = frappe.get_doc({"doctype": "Contact", "first_name": "Drawn", "last_name": "Check"}).insert(ignore_permissions=True)
	own = frappe.get_doc(
		{"doctype": "Contact", "first_name": "Own", "last_name": "Picture", "image": "/files/own-picture.png"}
	).insert(ignore_permissions=True)
	try:
		frappe.db.set_default(avatars.KEY, '{"Contact": "lorelei"}')
		drawn = faces.dress("Contact", plain.name)
		assert drawn and avatars.style_of(drawn) == "lorelei", drawn
		assert "<metadata" in open(frappe.get_site_path("public", drawn.lstrip("/")), encoding="utf-8").read(), "no credit in the picture"
		assert not faces.dress("Contact", own.name)
		avatars.pick("Contact", "initials")
		avatars.fill("Contact")
		assert avatars.style_of(frappe.db.get_value("Contact", plain.name, "image")) == "initials"
		assert frappe.db.get_value("Contact", own.name, "image") == "/files/own-picture.png"
		frappe.db.set_default(avatars.KEY, "{}")
		avatars.fill("Contact")
		assert not frappe.db.get_value("Contact", plain.name, "image")
		assert frappe.db.get_value("Contact", own.name, "image") == "/files/own-picture.png"
	finally:
		frappe.db.set_default(avatars.KEY, before or "{}")
		for name in (plain.name, own.name):
			frappe.delete_doc("Contact", name, ignore_permissions=True, force=True)
		avatars.fill("Contact")


@check
def one_follows_the_news():
	"""News Sources fetch on their own (one/news): a feed's new items are
	kept and its oldest let go, Google News asks OneAdmin and never Google,
	and nothing while it is off,
	OneAI's headlines come through the account, a Written source takes the
	items written for it, and each person's bar and each screen read them.
	Nothing leaves: the feed and the account are stood in for."""
	from unittest import mock

	from onedesk.one import announcements, news
	from onedesk.one.news import desk, feeds, fetching
	from onedesk.one.news import library as news_library
	from onedesk.trust_center import services

	rss = (
		b'<rss version="2.0"><channel><title>Check</title><link>https://check.example.com/</link>'
		b"<item><title>First headline</title><guid>1</guid><link>https://check.example.com/1</link><pubDate>Sat, 31 Oct 2026 06:00:00 GMT</pubDate></item>"
		b"<item><title>Second headline</title><guid>2</guid><link>https://check.example.com/2</link><pubDate>Sat, 31 Oct 2026 07:00:00 GMT</pubDate></item>"
		b"</channel></rss>"
	)
	names = ("Check Feed", "Check Google", "Check OneAI", "Check Written")
	with as_user(OWNER):
		was = services.on(fetching.GOOGLE_SERVICE)
		try:
			kinds = (("Feed", {"feed_url": "https://check.example.com/rss"}), ("Google News", {"google_topic": "Business"}), ("OneAI", {"ai_brief": "news for a glazing company", "fetch_every": "At Set Times", "fetch_at": "07:00"}), ("Written", {}))
			for name, (kind, extra) in zip(names, kinds, strict=True):
				frappe.get_doc({"doctype": news.SOURCE, "source_name": name, "kind": kind, "category": "Check News", "keep": 1 if kind == "Feed" else 0, **extra}).insert()
			assert frappe.db.exists(news.CATEGORY, "Check News"), "a category is made when it is first named"

			with mock.patch.object(feeds, "get", return_value=(200, rss, '"e1"', "Sat, 31 Oct 2026 07:00:00 GMT")) as got:
				assert fetching.fetch("Check Feed") == 2
			kept = frappe.get_all(news.ITEM, filters={"source": "Check Feed"}, pluck="title")
			assert kept == ["Second headline"], f"Keep 1 holds only the newest: {kept}"
			source = frappe.db.get_value(news.SOURCE, "Check Feed", ["etag", "website", "next_fetch", "last_error"], as_dict=True)
			assert source.etag == '"e1"' and source.website == "https://check.example.com/" and source.next_fetch and not source.last_error
			with mock.patch.object(feeds, "get", return_value=(304, b"", '"e1"', None)) as got:
				assert fetching.fetch("Check Feed") == 0
				assert got.call_args.args[1] == '"e1"', "the feed is asked whether it changed"

			services.switch(fetching.GOOGLE_SERVICE, 0)
			frappe.local.one_services = {}
			with mock.patch("onedesk.one.account.ask") as asked:
				fetching.fetch("Check Google")
				asked.assert_not_called()
			assert "TrustCenter" in frappe.db.get_value(news.SOURCE, "Check Google", "last_error"), "off, Google News is not asked"
			services.switch(fetching.GOOGLE_SERVICE, 1)
			frappe.local.one_services = {}
			google = frappe.get_doc(news.SOURCE, "Check Google")
			google.fetch_every = "15 Minutes"
			google.save()
			assert google.fetch_every == "Hourly", "how often Google News is fetched is not the workspace's to set"
			with mock.patch.object(feeds, "get") as got, mock.patch("onedesk.one.account.ask", return_value={"items": [], "waiting": True}) as asked:
				assert fetching.fetch("Check Google") == 0
				got.assert_not_called()
			assert asked.call_args.args[0] == fetching.GOOGLE and asked.call_args.kwargs["topic"] == "Business", "the workspace asks OneAdmin, never Google"
			soon = frappe.db.get_value(news.SOURCE, "Check Google", "next_fetch")
			assert soon <= frappe.utils.add_to_date(None, minutes=fetching.GOOGLE_WAITING + 1), "a first edition is asked again soon"
			headline = {"guid": "g1", "title": "Gold falls", "link": "https://check.example.com/g1", "published": "2026-10-31T05:00:00", "publisher": "Reuters", "publisher_site": "reuters.com"}
			with mock.patch("onedesk.one.account.ask", return_value={"items": [headline], "waiting": False}):
				assert fetching.fetch("Check Google") == 1
			assert frappe.db.get_value(news.SOURCE, "Check Google", "next_fetch") > frappe.utils.add_to_date(None, minutes=fetching.GOOGLE_EVERY - 1)

			said = {"items": [{"title": "Towers rise", "summary": "Output rose.", "publisher": "thenationalnews.com", "publisher_site": "thenationalnews.com"}]}
			with mock.patch("onedesk.one.account.ask", return_value=said) as asked:
				assert fetching.fetch("Check OneAI") == 1
				assert asked.call_args.args[0] == fetching.AI and asked.call_args.kwargs["brief"] == "news for a glazing company"
			assert frappe.db.get_value(news.ITEM, {"source": "Check OneAI"}, "publisher_site") == "thenationalnews.com"

			frappe.get_doc({"doctype": news.ITEM, "source": "Check Written", "title": "Our own news"}).insert()
			try:
				frappe.get_doc({"doctype": news.ITEM, "source": "Check Feed", "title": "Typed in"}).insert()
			except frappe.ValidationError:
				pass
			else:
				raise AssertionError("a feed's items are only fetched")

			desk.follow(["Check Written"])
			assert {one["title"] for one in desk.headlines()} == {"Our own news"}, "the bar reads the sources this person follows"
			assert desk.headlines()[0]["route"][1] == news.ITEM, "a written headline opens here"
			announcements.shows("News")
			now = announcements.current()
			assert now["shows"] == "News" and now["news"][0]["title"] == "Our own news"

			from onedesk.one.news import adding

			page = b'<html><head><meta property="og:site_name" content="Check Site"><link rel="alternate" type="application/rss+xml" href="/rss"></head></html>'
			with mock.patch.object(feeds, "get", side_effect=[(200, page, None, None), (200, rss, None, None)]):
				found = adding.find("check.example.com")
			assert found["url"] == "https://check.example.com/rss" and found["name"] == "Check Site" and len(found["headlines"]) == 2, found
			assert found["there"] == "Check Feed", "a feed already a source says so"
			with mock.patch.object(feeds, "get", return_value=(200, b"<html></html>", None, None)):
				assert "error" in adding.find("nothing.example.com")
			made = adding.add("Written", "Check Written")
			assert made == "Check Written 2", "a name already taken gets a number"
			frappe.delete_doc(news.SOURCE, made, force=True)
			assert adding.start()["google"]
			latest = adding.latest("Check OneAI")
			assert latest["items"][0]["title"] == "Towers rise" and latest["fetched"]
			assert adding.add_many([]) == []

			found = news_library.search("khaleej", "", "AE")
			assert [one["name"] for one in found["feeds"]] == ["Khaleej Times"] and "World" in found["categories"]
			url = found["feeds"][0]["url"]
			had = frappe.db.get_value(news.SOURCE, {"feed_url": url}, "name")
			added = news_library.add(url)
			assert frappe.db.get_value(news.SOURCE, added, "kind") == "Feed" and news_library.search("khaleej", "", "AE")["feeds"][0]["added"]
			assert not had or added == had, "a feed already added is not added twice"
			added = None if had else added
			following = desk.following()
			assert "Check Written" in {one["name"] for one in following["sources"] if one["followed"]}
			with mock.patch("frappe.enqueue") as queued:
				fetching.fetch_now("Check Feed")
				assert queued.call_args.kwargs["name"] == "Check Feed", "Fetch Now asks in the background"

			rows = news.items(list(names), most=10, order="By Category")
			assert {"category", "colour", "logo", "publisher"} <= set(rows[0]), "a ticker gets each headline's category and logo"
		finally:
			desk.follow([])
			frappe.defaults.clear_user_default(announcements.SHOWS)
			for name in (*names, locals().get("added")):
				if name and frappe.db.exists(news.SOURCE, name):
					frappe.delete_doc(news.SOURCE, name, force=True)
			services.switch(fetching.GOOGLE_SERVICE, int(was))
			frappe.local.one_services = {}


@check
def oneadmin_fetches_google_news_gently():
	"""OneAdmin alone reaches Google News (one_admin/google_news.py): a first
	ask is answered waiting and fetched at the next tick, two workspaces
	share one fetch, a fresh edition is not fetched again, a refusal pauses
	every fetch, and a workspace follows ten editions at most. Google is
	stood in for."""
	from unittest import mock

	from onedesk.one.news import feeds
	from onedesk.one_admin import google_news, site
	from onedesk.one_admin.faults import Refused

	rss = (
		b'<rss version="2.0"><channel><title>Google News</title>'
		b"<item><title>Gold falls - Reuters</title><guid>g1</guid><link>https://check.example.com/g1</link>"
		b'<pubDate>Sat, 31 Oct 2026 06:00:00 GMT</pubDate><source url="https://www.reuters.com">Reuters</source></item>'
		b"</channel></rss>"
	)
	tenants = ("check-news-a", "check-news-b")
	names = set()
	try:
		first = google_news.headlines(tenants[0], "Business", "", "AE", "en")
		assert first == {"items": [], "fetched": 0, "waiting": True}, first
		google_news.headlines(tenants[1], "Business", "", "AE", "en")
		names = google_news._names()
		with mock.patch.object(site, "is_admin", return_value=True), mock.patch.object(
			feeds, "get", return_value=(200, rss, None, None)
		) as got:
			google_news.tick()
			google_news.tick()
		assert got.call_count == 1, "two workspaces share one fetch, and a fresh edition waits its turn"
		said = google_news.headlines(tenants[1], "Business", "", "AE", "en")
		assert not said["waiting"] and said["items"][0]["title"] == "Gold falls"
		assert said["items"][0]["publisher_site"] == "reuters.com" and said["items"][0]["published"].startswith("2026-10-31")

		google_news.headlines(tenants[0], "", "glass facades", "AE", "en")
		names = google_news._names()
		with mock.patch.object(site, "is_admin", return_value=True), mock.patch.object(
			feeds, "get", side_effect=feeds.Unreadable("Google answered 503.")
		):
			google_news.tick()
		paused = frappe.cache.get_value(google_news.PAUSED)
		assert paused and paused["pauses"] == 1, "a refusal pauses every fetch"
		with mock.patch.object(site, "is_admin", return_value=True), mock.patch.object(feeds, "get") as got:
			google_news.tick()
			got.assert_not_called()
		with mock.patch.object(feeds, "get") as got:
			google_news.tick()
			got.assert_not_called()

		for n in range(google_news.MOST_A_WORKSPACE - 1):
			google_news.headlines(tenants[1], "", f"check words {n}", "AE", "en")
		names = google_news._names()
		try:
			google_news.headlines(tenants[1], "", "one too many", "AE", "en")
		except Refused:
			pass
		else:
			raise AssertionError("a workspace follows ten editions at most")
	finally:
		frappe.cache.delete_value(google_news.PAUSED)
		for name in names:
			frappe.cache.delete_value(google_news.HELD.format(name))
			frappe.cache.srem(google_news.EDITIONS, name)
		for tenant in tenants:
			frappe.cache.delete_value(google_news.FOLLOWED.format(tenant))


@check
def one_shows_the_weather_for_its_places():
	"""A place is found by its name and its weather comes through the account,
	once for every workspace near it (one/weather.py, one_admin/weather.py).
	Off, nothing is asked; on, the default place is shown beside the clock in
	the workspace's units. The account is stood in for: no call leaves."""
	from unittest import mock

	from onedesk.one import weather
	from onedesk.trust_center import services

	start = 1_793_433_600
	answer = {
		"place": "25.3,55.3",
		"offset": 4 * 3600,
		"hours": [{"dt": start + i * 3600, "temp": 30 + i, "humidity": 40, "wind_speed": 5, "code": 800} for i in range(20)],
		"days": [{"dt": start + i * 86400, "high": 33, "low": 26, "code": 801} for i in range(10)],
		"credits": 0,
	}
	place = frappe.db.get_value("Weather Place", {"is_default": 1}, "name")
	assert place, "the demo has a default place"
	with as_user(OWNER):
		was = services.on(weather.SERVICE)
		try:
			services.switch(weather.SERVICE, 0)
			frappe.local.one_services = {}
			weather.forget(place)
			with mock.patch("onedesk.one.account.ask") as asked:
				assert weather.here() is None, "off, nothing is shown"
				try:
					weather.search("Dubai")
				except frappe.ValidationError:
					pass
				else:
					raise AssertionError("off, no place can be searched for")
				asked.assert_not_called()
			services.switch(weather.SERVICE, 1)
			frappe.local.one_services = {}
			found = [{"name": "دبي", "region": "Dubai", "country": "AE", "latitude": 25.2647, "longitude": 55.2924}]
			with mock.patch("onedesk.one.account.ask", return_value=found) as asked:
				assert weather.search("Dubai") == found
				assert asked.call_args.args[0] == weather.PLACES and asked.call_args.kwargs["query"] == "Dubai"
				listed = weather.suggest("Dubai")
				assert listed[0]["value"] == "دبي, Dubai, AE" and listed[0]["label"] == "دبي", "towns sharing a name are told apart"
			assert weather.suggest("D") == [], "one letter asks nothing"
			with mock.patch("frappe.get_request_header", side_effect={"X-One-City": "Al%20Barsha", "X-One-Region": "Dubai", "X-One-Country": "AE", "X-One-Latitude": "25.11", "X-One-Longitude": "55.19"}.get):
				assert weather.located() == {"name": "Al Barsha", "region": "Dubai", "country": "AE", "latitude": 25.11, "longitude": 55.19}
			with mock.patch("frappe.get_request_header", return_value=None):
				assert weather.located() == {}, "without the edge's headers, where it is is not guessed"
			with mock.patch("onedesk.one.account.ask", return_value=dict(answer)) as asked, mock.patch.object(weather, "_now", return_value=start + 60):
				shown = weather.here()
				assert shown["place"] == place and shown["temperature"] == "30°C" and len(shown["hours"]) == 13, shown
				assert asked.call_args.args[0] == weather.READING and set(asked.call_args.kwargs) == {"latitude", "longitude"}
				weather.here()
				assert asked.call_count == 1, "the account's answer is kept a quarter of an hour"
		finally:
			weather.forget(place)
			services.switch(weather.SERVICE, int(was))
			frappe.local.one_services = {}


@check
def shortcuts_move_for_the_reader_alone():
	"""ShortcutCenter (one/shortcut_center.py): every module's shortcuts.py
	read beside the others, each with its own id. Nadia moves Search to
	Ctrl+Shift+F; it is hers, Karim's is as shipped. Moved back to its own keys
	it is no longer kept; a key the browser keeps is refused; reset puts every
	one back."""
	from onedesk.one import shortcut_center

	ids = [one["id"] for one in shortcut_center.declared()]
	assert len(ids) == len(set(ids)), "two shortcuts share an id"
	assert "one_interface.search" in ids and "one_mail.next" in ids, ids
	shipped = next(one for one in shortcut_center.declared() if one["id"] == "one_interface.search")["keys"]
	with as_user("nadia@one.test"):
		try:
			said = shortcut_center.save("one_interface.search", '["mod+shift+KeyF"]')
			assert said.get("one_interface.search") == ["mod+shift+KeyF"], said
			with as_user("karim@one.test"):
				assert "one_interface.search" not in shortcut_center.yours()
			assert "one_interface.search" not in shortcut_center.save("one_interface.search", list(shipped))
			try:
				shortcut_center.save("one_interface.search", '["mod+KeyW"]')
			except frappe.ValidationError:
				pass
			else:
				raise AssertionError("a key the browser keeps was taken as a shortcut")
		finally:
			assert shortcut_center.reset() == {}


@check
def turn_off_these_emails_works_without_signing_in():
	"""A notification's mail carries a signed link (unsubscribe.link): opened
	as Guest, or posted by a mail client's one-click, it turns that one type's
	email off for Nadia as NotificationCenter's switch does, and Turn On
	Again puts it back. A link with its address changed does nothing."""
	from urllib.parse import parse_qsl

	from werkzeug.test import EnvironBuilder
	from werkzeug.wrappers import Request

	from onedesk.one import notification_center, unsubscribe

	def mailed(kind):
		with as_user("nadia@one.test"):
			return next(one for one in notification_center.yours()["types"] if one["name"] == kind)["email"]

	def opened(url, method="GET"):
		query = url.split("?", 1)[1]
		data = {"List-Unsubscribe": "One-Click"} if method == "POST" else None
		frappe.local.request = Request(EnvironBuilder(method=method, query_string=query, data=data).get_environ())
		said = dict(parse_qsl(query))
		with as_user("Guest"):
			if "unsubscribe.on" in url:
				unsubscribe.on(said["email"], said["doctype"], said["name"])
			else:
				unsubscribe.off(said["email"], said["doctype"], said["name"])
		return frappe.local.message_title

	was_request = getattr(frappe.local, "request", None)
	with as_user("nadia@one.test"):
		kind = next(one["name"] for one in notification_center.yours()["types"] if one["may_email"] and one["email"])
	assert unsubscribe.offered("nadia@one.test", kind) == kind
	email = frappe.db.get_value("User", "nadia@one.test", "email")
	try:
		forged = unsubscribe.link(email, kind).replace("nadia", "omar")
		assert opened(forged) == "This link no longer works" and mailed(kind)
		assert opened(unsubscribe.link(email, kind), "POST") == "Emails Turned Off" and not mailed(kind)
		assert opened(unsubscribe.link(email, kind, unsubscribe.AGAIN)) == "Emails Turned On" and mailed(kind)
		assert opened(unsubscribe.link(email, kind)) == "Emails Turned Off" and not mailed(kind)
	finally:
		frappe.local.request = was_request
		with as_user("nadia@one.test"):
			notification_center.choose(kind, "email", 1)
