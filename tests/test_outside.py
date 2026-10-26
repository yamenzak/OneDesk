"""A workspace's desk is One's (one/outside.py): frappe's, erpnext's and
hrms's own sidebars and workspaces are left out of the boot for everyone, a
System Manager included, and their addresses and frappe's apps screen go to
One's Home. These read the code that says so."""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SOURCE = (tree.APP / "one" / "outside.py").read_text()


def test_the_boot_carries_ones_sidebars_and_workspaces_only():
	assert 'APP = "onedesk"' in SOURCE and 'FIRST = "One"' in SOURCE
	assert "platform()" not in SOURCE and "def platform" not in (tree.APP / "one" / "boot.py").read_text()
	assert 'page.get("app") in held' in SOURCE and "held = {APP, *private.names()}" in SOURCE and '["has_create_access"] = False' in SOURCE
	assert "outside.keep(bootinfo)" in (tree.APP / "one" / "boot.py").read_text()
	assert "outside.kept(said)" in (tree.APP / "one" / "reports.py").read_text()


def test_elsewhere_and_the_apps_screen_go_to_ones_home():
	desk = (tree.APP / "public" / "js" / "desk.js").read_text()
	assert 'for (const slug of frappe.boot.one_elsewhere) frappe.re_route[slug] = "one";' in desk
	assert 'frappe.re_route[""] = "one";' in desk
	assert 'page["name"].lower().replace(" ", "-")' in SOURCE


def test_menus_offer_no_screen_the_reader_cannot_open():
	"""Gap 5: each item that ends on a System Manager's screen is offered on
	frappe's own read check of it, and Import not at all."""
	js = (tree.APP / "public" / "js" / "outside.js").read_text()
	assert 'frappe.model.can_read("Audit Trail")' in js
	assert 'frappe.model.can_read("Auto Email Report")' in js
	assert "if (!frappe.boot.one_elsewhere) return super.setup_menu();" in js
	assert '"/assets/onedesk/js/outside.js"' in (tree.APP / "hooks.py").read_text()
	assert 'bootinfo["user"]["can_import"] = []' in SOURCE
	declutter = (tree.APP / "one" / "declutter.py").read_text()
	assert '"System Health": "frappe.model.can_read(\'System Health Report\')"' in declutter


def test_frappes_furniture_editors_are_not_offered():
	"""Gap 6: Edit Sidebar and Manage Dock arrange frappe's sidebars and dock,
	and the sidebar's header opens no menu at all: frappe's switched to other
	apps and frappe's own desk."""
	js = (tree.APP / "public" / "js" / "outside.js").read_text()
	assert '["workspace-selector"]' in js
	assert "if (frappe.boot.one_elsewhere && frappe.ui.Sidebar)" in js
	shell = (tree.APP / "public" / "js" / "shell.js").read_text()
	assert "Header.prototype.setup_menu = function () {};" in shell


def test_frappes_screens_open_ones_own():
	"""A list or form One has its own screen for opens that screen, replacing
	the history entry, and an address belongs to OneCRM beside its contact."""
	js = (tree.APP / "public" / "js" / "outside.js").read_text()
	for route in (
		'["one", { center: "account", at: "profile" }]',
		'["one", { center: "account", at: "people" }]',
		'["onecloud"]',
		'["my-tasks"]',
		'["workspace-settings", { section: "printing" }]',
	):
		assert route in js
	assert "frappe.route_flags.replace_route = true;" in js
	assert "onedesk.notification_center.open();" in js
	one = json.loads((tree.APP / "one" / "sidebar" / "one" / "one.json").read_text())
	links = [item.get("link_to") for item in one["items"]]
	assert links.index("Address") == links.index("Contact") + 1


def test_help_mail_and_search_are_ones():
	"""Gaps 7 to 9: the theme sits in the user menu, frappe's mail list and
	Inbox view open OneMail, and search offers One's pages and reports."""
	js = (tree.APP / "public" / "js" / "outside.js").read_text()
	assert "new frappe.ui.ThemeSwitcher().show()" in js
	assert 'return !name || name === "view" ? ["onemail"] : null;' in js
	assert "for (const name of onedesk.outside.SOURCES)" in js and "found.filter(onedesk.outside.offered)" in js


def test_frappes_error_pages_are_ones():
	"""Gap 10: the desk's not-found and not-permitted pages keep the rail, and
	frappe's web pages are drawn in One's portal look."""
	js = (tree.APP / "public" / "js" / "outside.js").read_text()
	assert (
		"frappe.show_not_found = (page_name) =>" in js and "frappe.show_not_permitted = (page_name) =>" in js
	)
	assert "frappe.ui.make_app_page({ parent: wrapper, single_column: true });" in js
	assert "frappe.views.pageview.show = function (name)" in js
	www = tree.APP / "www"
	for page in ("404", "message", "error"):
		assert "one-portal" in (www / f"{page}.html").read_text(), page
	assert "return message.get_context(context)" in (www / "message.py").read_text()
	assert "context.http_status_code = 404" in (www / "404.py").read_text()
	me = (www / "me.py").read_text()
	assert '"/desk/one?center=account&at=profile"' in me and '"/account"' in me and "/portal/profile" in me
	assert (
		'".for-login:not(.one-your-data) .page-card-body"'
		in (tree.APP / "public" / "js" / "login.js").read_text()
	)


def test_addresses_and_contacts_is_in_onecrm():
	"""Gap 11: erpnext's working report of a party's addresses and contacts,
	opening on customers. frappe's own files every row under the first party."""
	assert '"Report", "Address And Contacts"' in (tree.APP / "one_crm" / "home.py").read_text()
	reports = (tree.APP / "public" / "js" / "reports.js").read_text()
	assert (
		'"Address And Contacts": { party_type: ["Customer", "Lead", "Supplier", "Sales Partner"] }' in reports
	)
	assert "frappe.model.can_read(kind)" in reports


def test_not_found_and_errors_are_one_scene():
	"""The web's 404, error and message pages and the desk's not found and no
	access draw the same scene: One's ring for the 0, centred, with a way back."""
	www = tree.APP / "www"
	for page in ("404", "error", "message"):
		html = (www / f"{page}.html").read_text()
		assert '{% include "templates/includes/one_lost.html" %}' in html and "one-lost" in html, page
	js = (tree.APP / "public" / "js" / "outside.js").read_text()
	assert "onedesk.outside.lost(art)" in js and 'class="one-lost one-lost--desk"' in js
	assert 'code: "403",' in js
	message = (www / "message.html").read_text()
	assert 'code|length == 3 and code[1] == "0"' in message
	assert '403 if title == _("Not Permitted")' in message
	assert "const id = `one-lost-${++drawn}`;" in js
	hooks = (tree.APP / "hooks.py").read_text()
	assert hooks.count('"/assets/onedesk/css/lost.css"') == 2
	assert "prefers-reduced-motion" in (tree.APP / "public" / "css" / "lost.css").read_text()


def test_a_kind_of_record_not_readable_is_no_access_and_a_missing_page_404():
	"""A kind of record not in the reader's boot is taken for a page by the
	router; it says No access. A web page frappe calls 404 is drawn as 404."""
	js = (tree.APP / "public" / "js" / "outside.js").read_text()
	assert '.xcall("onedesk.one.outside.kind_of", { name })' in js
	assert "def kind_of(name: str) -> bool:" in SOURCE and "@frappe.whitelist()" in SOURCE
	error = (tree.APP / "www" / "error.py").read_text()
	assert "if code == 404:" in error
	assert '{% if error and code.startswith("5") %}' in (tree.APP / "www" / "error.html").read_text()


SEARCH = Path("/home/frappe/bench1/apps/frappe/frappe/public/js/frappe/ui/toolbar/search_utils.js")
OUTSIDE_JS = (tree.APP / "public" / "js" / "outside.js").read_text()


def _listed(name: str) -> list[str]:
	body = OUTSIDE_JS.split(f"onedesk.outside.{name} = ", 1)[1].split(";\n", 1)[0]
	return re.findall(r'"?(get_\w+)"?\s*[:,\]]', body)


def test_every_source_of_frappes_search_bar_is_filtered():
	"""A source frappe adds to its search bar is either filtered by what One
	shows or named, with why, as left out of it."""
	if not SEARCH.exists():
		return
	theirs = set(re.findall(r"^\t(get_\w+)(?::\s*function)?\s*\(", SEARCH.read_text(), re.M))
	ours = set(_listed("SOURCES")) | set(_listed("UNFILTERED"))
	assert theirs and theirs <= ours, f"frappe's search bar draws from {sorted(theirs - ours)}: add it to SOURCES in outside.js"


def test_pickers_and_global_search_offer_what_one_shows():
	"""A picker of record types or reports, which is also what a Dynamic Link
	asks first, and frappe's global search offer only `shown`."""
	hooks = (tree.APP / "hooks.py").read_text()
	assert '"DocType": "onedesk.one.outside.doctype_query"' in hooks and '"Report": "onedesk.one.outside.report_query"' in hooks
	assert '"frappe.utils.global_search.search": "onedesk.one.outside.search"' in hooks
	assert 'clear_cache = ["onedesk.one.outside.forget"]' in hooks


MACHINERY = (
	"DocType", "DocField", "Module Def", "Workspace", "Workspace Sidebar", "Custom Field", "Property Setter",
	"Server Script", "Client Script", "Report", "Page", "Scheduled Job Type", "RQ Job", "Error Log",
	"Installed Application", "Patch Log", "Data Import", "Form Tour", "Onboarding Step", "Module Onboarding",
	"Website Settings", "Web Page", "System Settings", "Role Permission for Page and Report",
)


def test_frappes_machinery_is_never_shown():
	"""`shown.json` is written by the atlas (scripts/docs.py keeps it current);
	none of frappe's own building blocks is in it."""
	said = json.loads((tree.APP / "one" / "shown.json").read_text())
	assert set(said) == {"_", "DocType", "Report", "Page", "Dashboard", "Workspace"}
	assert not set(MACHINERY) & set(said["DocType"])
	assert said["Workspace"] and all(name in ("One",) or name.startswith("One") for name in said["Workspace"])


def test_a_rails_dashboard_stays_in_its_rail():
	"""OneHR's Recruitment Overview opens in OneHR; a tool's record no rail
	lists opens in One, under Workspace Settings."""
	js = (tree.APP / "public" / "js" / "desk.js").read_text()
	assert "this.get_modules_linking(entity, super.link_type_from_route(route)).length" in js
	assert "OneSidebar.workspace(route) &&" not in js and "if (OneSidebar.workspace(route)) return" not in js


def test_frappes_documentation_links_are_gone():
	"""An empty list, a list's and a form's menu, a report and a field's help
	link to frappe's, erpnext's and hrms's documentation; the meta loses them
	before anything draws."""
	assert "delete doc.documentation;" in OUTSIDE_JS and "delete field.documentation_url;" in OUTSIDE_JS
	assert "delete doc.documentation_url;" in OUTSIDE_JS and "frappe.model.sync = function" in OUTSIDE_JS
