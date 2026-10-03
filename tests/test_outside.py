"""A workspace's desk is One's (one/outside.py): frappe's, erpnext's and
hrms's own sidebars and workspaces are left out of the boot for everyone but
the platform's own people, and their addresses and frappe's apps screen go to
One's Home. These read the code that says so."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SOURCE = (tree.APP / "one" / "outside.py").read_text()


def test_the_boot_carries_ones_sidebars_and_workspaces_only():
	assert 'APP = "onedesk"' in SOURCE and 'FIRST = "One"' in SOURCE
	assert SOURCE.count("if platform():") == 2
	assert '(sidebar or {}).get("app") == APP' in SOURCE
	assert 'page.get("app") == APP' in SOURCE and '["has_create_access"] = False' in SOURCE
	assert "outside.keep(bootinfo)" in (tree.APP / "one" / "boot.py").read_text()
	# A sidebar swapped in after a change is held to the same.
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
	# Print Settings an administrator may only read: off One's desk for everyone.
	assert "if (!frappe.boot.one_elsewhere) return super.setup_menu();" in js
	assert '"/assets/onedesk/js/outside.js"' in (tree.APP / "hooks.py").read_text()
	assert 'bootinfo["user"]["can_import"] = []' in SOURCE
	declutter = (tree.APP / "one" / "declutter.py").read_text()
	assert '"System Health": "frappe.model.can_read(\'System Health Report\')"' in declutter


def test_frappes_furniture_editors_are_not_offered():
	"""Gap 6: Edit Sidebar and Manage Dock arrange frappe's sidebars and dock."""
	js = (tree.APP / "public" / "js" / "outside.js").read_text()
	assert '"edit-sidebar"' in js and '["workspace-selector"]' in js
	assert "if (frappe.boot.one_elsewhere && frappe.ui.SidebarHeader && frappe.ui.Sidebar)" in js


def test_frappes_screens_open_ones_own():
	"""A list or form One has its own screen for opens that screen, replacing
	the history entry, and an address belongs to OneCRM beside its contact."""
	js = (tree.APP / "public" / "js" / "outside.js").read_text()
	for route in (
		'["settings", { section: "notifications" }]',
		'["settings", { section: "profile" }]',
		'["workspace-settings", { section: "people" }]',
		'["onecloud"]',
		'["my-tasks"]',
		'["workspace-settings", { section: "printing" }]',
	):
		assert route in js
	assert "frappe.route_flags.replace_route = true;" in js
	crm = json.loads((tree.APP / "one_crm" / "sidebar" / "onecrm" / "onecrm.json").read_text())
	links = [one.get("link_to") for one in crm["items"]]
	assert links.index("Address") == links.index("Contact") + 1


def test_help_mail_and_search_are_ones():
	"""Gaps 7 to 9: Help asks OneAI, the theme sits in the user menu, frappe's
	mail list and Inbox view open OneMail, and search offers One's pages and
	reports."""
	js = (tree.APP / "public" / "js" / "outside.js").read_text()
	assert "get_help_siblings()" in js and '__("Ask OneAI")' in js
	assert "new frappe.ui.ThemeSwitcher().show()" in js and '["edit-sidebar", "all-apps"]' in js
	assert 'return !name || name === "view" ? ["onemail"] : null;' in js
	assert "utils.get_pages = function" in js and "utils.get_reports = function" in js
	assert 'app_of(info[name]?.module) === "onedesk"' in js


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
	for page in ("404", "message", "error", "me"):
		assert "one-portal" in (www / f"{page}.html").read_text(), page
	assert "return message.get_context(context)" in (www / "message.py").read_text()
	assert "context.http_status_code = 404" in (www / "404.py").read_text()
	me = (www / "me.py").read_text()
	assert '"/desk/settings?section=profile"' in me and '"/account"' in me
	# The passkey button is the sign-in card's, not Set Password's.
	assert '".for-login .page-card-body"' in (tree.APP / "public" / "js" / "login.js").read_text()


def test_addresses_and_contacts_is_in_onecrm():
	"""Gap 11: erpnext's working report of a party's addresses and contacts,
	opening on customers. frappe's own files every row under the first party."""
	crm = json.loads((tree.APP / "one_crm" / "sidebar" / "onecrm" / "onecrm.json").read_text())
	assert "Address And Contacts" in [one.get("link_to") for one in crm["items"]]
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
	# No access is 403 on the desk and off it, the ring the 0 of any such code.
	assert 'code: "403",' in js
	message = (www / "message.html").read_text()
	assert 'code|length == 3 and code[1] == "0"' in message
	assert '403 if title == _("Not Permitted")' in message
	# Gradient ids per drawing, so a hidden page's scene cannot leave this one's ring undrawn.
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
