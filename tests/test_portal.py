"""The portal a workspace's customers and suppliers sign in to (one/portal.py):
frappe's own pages and erpnext's list contexts, drawn in One's look."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SOURCE = (tree.APP / "one" / "portal.py").read_text()
HOOKS = (tree.APP / "hooks.py").read_text()
INCLUDES = tree.APP / "templates" / "includes"


def test_the_portal_lists_in_ones_look_on_frappes_context():
	page = (tree.APP / "www" / "portal.html").read_text()
	assert '{% include "templates/includes/one_portal_head.html" %}' in page
	assert "{%- set show_sidebar = False -%}" in page
	assert "{% for row in result %}{{ row }}{% endfor %}" in page
	# Frappe's own context, which lists through each kind's get_list_context.
	assert "return portal.get_context(context, **dict_params)" in (tree.APP / "www" / "portal.py").read_text()
	for method in ("one_portal_tabs", "one_portal_tone", "one_portal_home"):
		assert f'"onedesk.one.portal.{method}"' in HOOKS


def test_every_row_erpnext_and_frappe_draw_is_ones():
	for row in (
		"transaction_row.html",
		"projects/project_row.html",
		"timesheet/timesheet_row.html",
		"list/row_template.html",
	):
		html = (INCLUDES / row).read_text()
		assert "one-list__row" in html, row
		assert "col-sm-" not in html and "web-list-item" not in html, row


def test_the_tabs_are_portal_settings_by_role():
	assert "get_portal_sidebar_items()" in SOURCE
	assert 'OFF = ("/issues", "/material-requests")' in SOURCE
	assert '"/rfq": "Quote Requests"' in SOURCE
	assert '"onedesk.one.portal.settle",' in HOOKS
	assert "onedesk.one.patches.portal_settle" in (tree.APP / "patches.txt").read_text()


def test_a_customers_or_suppliers_contact_is_a_portal_user():
	assert 'PARTIES = ("Customer", "Supplier")' in SOURCE
	assert 'party.append("portal_users", {"user": doc.user})' in SOURCE
	assert '"onedesk.one.portal.invited"' in HOOKS.split('"Contact": {', 1)[1].split("},", 1)[0]


def test_the_portal_is_drawn_as_frappe_ui_draws_it():
	"""Each part as frappe-ui draws it, on espresso's tokens: the head's Avatar
	and Dropdown, TabButtons with frappe's Lucide icons, ListView's head row,
	Badge; on a wide screen Sidebar and PageHeader in place of the head and
	the tabs; and close to the edge on a phone."""
	head = (INCLUDES / "one_portal_head.html").read_text()
	assert 'class="one-avatar"' in head and 'href="/logout"' in head
	assert 'class="one-tab-buttons"' in head and '<use href="#icon-{{ tab.icon }}">' in head
	side = (INCLUDES / "one_portal_sidebar.html").read_text()
	assert 'class="one-sidebar__trigger"' in side and 'href="/logout"' in side and "me.party" in side
	assert '<use href="#icon-{{ tab.icon }}">' in side
	page = (tree.APP / "www" / "portal.html").read_text()
	assert "one_portal_sidebar.html" in page and "set full_width = True" in page
	assert "one_portal_columns(row_template)" in page and 'class="one-search"' in page
	css = (tree.APP / "public" / "css" / "portal.css").read_text()
	block = css.split("/* The portal a workspace's customers and suppliers sign in to (one/portal.py),", 1)[1]
	for token in ("var(--surface-gray-2)", "var(--ink-gray-5)", "var(--surface-amber-2)"):
		assert token in block
	assert "#" not in "".join(
		line for line in block.splitlines() if "color:" in line or "background:" in line
	)
	assert "padding: 1rem 1rem 3rem;" in block
	assert "width: 15rem;" in block and "var(--surface-sidebar" in block
	assert "ICONS = {" in SOURCE and "COLUMNS = {" in SOURCE


def test_a_record_page_is_the_portals():
	"""erpnext's record page for the seven kinds, in the portal's shell: its
	own context first (the reader's permission, Pay), then Breadcrumbs, the
	Badge, Download PDF, the facts, the items as ListView and the totals."""
	py = (tree.APP / "www" / "order.py").read_text()
	assert "order.get_context(context)" in py
	page = (tree.APP / "www" / "order.html").read_text()
	assert "one_portal_sidebar.html" in page and "one_portal_head.html" in page
	assert 'class="one-crumbs"' in page and "one_portal_record(doc)" in page
	assert "frappe.utils.print_format.download_pdf" in page and "show_pay_button" in page
	assert "{% if doc.docstatus == 1 %}" in page
	assert "FACTS = (" in SOURCE and "OWED = (" in SOURCE
	assert '"terms": sanitize_html(doc.terms)' in SOURCE
	side = (INCLUDES / "one_portal_sidebar.html").read_text()
	assert "one_portal_at_home()" in side and "tab.current" in side


def test_a_supplier_answers_a_quote_request_on_the_portal():
	"""erpnext's request page, in the portal's shell: the rows priced in place
	and sent through one/portal.send_quote, which reads everything but the
	rate, quantity and notes from the request itself, checks the reader is the
	supplier's portal user, keeps the quote theirs, and tells the buyer."""
	page = (tree.APP / "www" / "rfq.html").read_text()
	assert "rfq.get_context(context)" in (tree.APP / "www" / "rfq.py").read_text()
	assert "one_portal_rfq(doc)" in page and "onedesk.one.portal.send_quote" in page
	assert "doc.as_json()" not in page and "rfq.js" not in page
	send = SOURCE.split("def send_quote", 1)[1].split("\ndef ", 1)[0]
	assert '@frappe.whitelist(methods=["POST"])\ndef send_quote' in SOURCE
	assert 'frappe.db.exists("Portal User", {"parent": supplier, "user": user})' in send
	assert "check_supplier_has_docname_access(supplier)" in send
	assert "for row in doc.items:" in send and "validate_existing_supplier_quotation" in send
	assert "finally:\n\t\tfrappe.session.user = user" in send
	assert 'quote.db_set({"owner": user, "modified_by": user}' in send
	assert 'notify.notify(\n\t\t"Quote Received"' in send
	row = (INCLUDES / "transaction_row.html").read_text()
	assert "one_portal_quoted(doc.name)" in row and "one_portal_status(" in row
	notes = (tree.APP / "one_inventory" / "notifications.py").read_text()
	assert '_lt("Quote Received")' in notes and '_lt("Quote Request Sent")' in notes


def test_the_rest_of_the_portal_is_in_its_shell():
	"""An address's form keeps the portal's shell (frappe's web form, extended
	by its app prefix), the list adds an address, a timesheet is listed once,
	and a project's page is the portal's."""
	form = (tree.APP / "website" / "doctype" / "web_form" / "templates" / "web_form.html").read_text()
	assert '{% extends "frappe/website/doctype/web_form/templates/web_form.html" %}' in form
	assert "one_portal_sidebar.html" in form and "{{ super() }}" in form
	assert "data-one-save" in form and 'requestSubmit()' in form and "MutationObserver" in form
	assert 'ADD = {"Address": ("/address/new", _lt("Add Address"))}' in SOURCE
	assert '"addresses": {"button_label": "Save Address"}' in SOURCE
	sheet = (INCLUDES / "timesheet" / "timesheet_row.html").read_text()
	assert "one_portal_timesheet(doc.name)" in sheet
	assert 'frappe.local.flags.setdefault("one_portal_timesheets", set())' in SOURCE
	project = (tree.APP / "www" / "projects.html").read_text()
	assert "one_portal_sidebar.html" in project and 'class="one-crumbs"' in project
	assert "{{ doc.name | e }}" not in (INCLUDES / "projects" / "project_row.html").read_text()


def test_the_account_pages_are_in_the_portals_shell():
	"""frappe's account pages for a portal user: /me lists Edit Profile,
	Change Password, Third Party Apps (once one is let in), Sign out and
	Delete Account (always, as on the desk); Third Party Apps keeps frappe's
	context and revoke call; Set Password reached from there says Change
	Password; the deletion form is worded by settle."""
	me = (tree.APP / "www" / "me.html").read_text()
	assert "one_portal_sidebar.html" in me and "/update-password" in me
	assert "{% if has_apps %}" in me and "show_deletion" not in me
	assert "/request-for-account-deletion/new?email=" in me
	assert '"OAuth Bearer Token"' in (tree.APP / "www" / "me.py").read_text()
	apps_py = (tree.APP / "www" / "third_party_apps.py").read_text()
	assert "from frappe.www.third_party_apps import get_context" in apps_py
	apps = (tree.APP / "www" / "third_party_apps.html").read_text()
	assert "one_portal_sidebar.html" in apps and "btn-delete-app" in apps
	assert 'include "templates/includes/integrations/third_party_apps.js"' in apps
	login = (tree.APP / "public" / "js" / "login.js").read_text()
	assert '__("Change Password")' in login and 'get_cookie("user_id")' in login
	assert 'ACCOUNT = ("/me",' in SOURCE and '"request-to-delete-data": {' in SOURCE
	assert "one_portal_here" in (tree.APP / "hooks.py").read_text()
