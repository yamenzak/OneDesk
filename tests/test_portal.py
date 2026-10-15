"""The portal a workspace's customers and suppliers sign in to: a frappe-ui
app (frontend/portal) on frappe's own sidebar items and erpnext's own list
and page contexts, which one/portal.py reads and answers as JSON."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SOURCE = (tree.APP / "one" / "portal.py").read_text()
HOOKS = (tree.APP / "hooks.py").read_text()
APP = tree.ROOT / "frontend" / "portal"
PAGES = APP / "src" / "pages"


def _page(name: str) -> str:
	return (PAGES / name).read_text()


def test_the_portal_is_a_frappe_ui_app_served_at_portal():
	"""frappe-ui's vite plugin builds it the way HRMS builds its PWA: the page
	at /portal and everything under it is www/portal.py, which sends a guest to
	sign in and someone with a desk to it, and starts the app with its boot."""
	vite = (APP / "vite.config.js").read_text()
	assert 'frontendRoute: "/portal"' in vite and "../../onedesk/www/portal.html" in vite
	assert '{"from_route": "/portal/<path:app_path>", "to_route": "portal"}' in HOOKS
	served = (tree.APP / "www" / "portal.py").read_text()
	assert "/login?redirect-to=" in served and '_go("/desk")' in served
	assert r'replace("<", "\\u003c")' in served, "the boot can't end its own script"
	assert "onedesk/www/portal.html" in (tree.ROOT / ".gitignore").read_text()
	assert json.loads((tree.ROOT / "frontend" / "package.json").read_text())["scripts"]["build"].endswith(
		"cd portal && vite build"
	)


def test_the_old_portal_is_gone_and_its_places_lead_to_the_app():
	"""erpnext's lists and record pages, its project page and frappe's address
	and profile forms are redirected into the app; none of the Jinja pages or
	row templates that drew them is left."""
	for gone in ("order.html", "rfq.html"):
		assert not (tree.APP / "www" / gone).exists(), gone
	includes = tree.APP / "templates" / "includes"
	for gone in ("one_portal_head.html", "one_portal_sidebar.html", "transaction_row.html", "address_row.html"):
		assert not (includes / gone).exists(), gone
	assert not (tree.APP / "website").exists()
	redirects = HOOKS.split("website_redirects = [", 1)[1].split("\n]", 1)[0]
	for where in ('"target": r"/portal/\\1\\2"', '"/portal/projects"', '"/portal/addresses/\\1"', '"/portal/profile"'):
		assert where in redirects, where
	assert "one_portal_" not in HOOKS


def test_the_tabs_are_portal_settings_by_role():
	assert "get_portal_sidebar_items()" in SOURCE
	assert 'OFF = ("/issues", "/material-requests")' in SOURCE
	assert '"/rfq": "Quote Requests"' in SOURCE
	assert '"onedesk.one.portal.settle",' in HOOKS
	assert "onedesk.one.patches.portal_settle" in (tree.APP / "patches.txt").read_text()


def test_a_customers_or_suppliers_contact_is_a_portal_user():
	assert 'PARTIES = ("Customer", "Supplier")' in SOURCE
	assert '{"doctype": "Portal User", **where, "user": doc.user}' in SOURCE
	assert '"onedesk.one.portal.invited"' in HOOKS.split('"Contact": {', 1)[1].split("},", 1)[0]


def test_the_portal_is_drawn_as_frappe_ui_draws_it():
	"""frappe-ui's DesktopShell with its Sidebar, or its MobileShell with a tab
	bar on a phone; each list frappe-ui's ListView, each page a PageHeader."""
	shell = (APP / "src" / "App.vue").read_text()
	assert "<DesktopShell" in shell and "<MobileShell" in shell and "<MobileNav" in shell
	assert "<Sidebar" in (APP / "src" / "parts" / "PortalSidebar.vue").read_text()
	assert "<PageHeader" in (APP / "src" / "parts" / "Head.vue").read_text()
	assert 'from "frappe-ui/list"' in _page("List.vue")
	assert "ICONS = {" in SOURCE and "COLUMNS = {" in SOURCE
	# Every icon a tab names is built: the class is found where tailwind looks.
	assert "portal.py" in (APP / "tailwind.config.js").read_text()


def test_a_record_page_is_the_portals():
	"""erpnext's record page context for the seven kinds first (the reader's
	permission, Pay), then the Badge, Download PDF, the facts, the items and
	the totals, answered by one/portal.record."""
	record = SOURCE.split("def record(", 1)[1].split("\ndef ", 1)[0]
	assert "from erpnext.templates.pages import order" in record and "_opened(doctype, name, order)" in record
	assert "frappe.utils.print_format.download_pdf" in record and "context.show_pay_button" in record
	assert "FACTS = (" in SOURCE and "OWED = (" in SOURCE
	assert '"terms": sanitize_html(doc.terms)' in SOURCE
	assert 'call("record"' in _page("Record.vue")


def test_a_supplier_answers_a_quote_request_on_the_portal():
	"""erpnext's request page context, which refuses a request not sent to the
	reader's supplier; the rows priced in place and sent through
	one/portal.send_quote, which reads everything but the rate, quantity and
	notes from the request itself, keeps the quote theirs, and tells the buyer."""
	rfq = SOURCE.split("def rfq(", 1)[1].split("\ndef ", 1)[0]
	assert "from erpnext.templates.pages import rfq as page" in rfq and 'doc.get("rfq_links")' in rfq
	assert "send_quote" in _page("Rfq.vue")
	send = SOURCE.split("def send_quote", 1)[1].split("\ndef ", 1)[0]
	assert '@frappe.whitelist(methods=["POST"])\ndef send_quote' in SOURCE
	assert 'frappe.db.exists("Portal User", {"parent": supplier, "user": user})' in send
	assert "check_supplier_has_docname_access(supplier)" in send
	assert "for row in doc.items:" in send and "validate_existing_supplier_quotation" in send
	assert "finally:\n\t\tfrappe.session.user = user" in send
	assert 'quote.db_set({"owner": user, "modified_by": user}' in send
	assert "tell.quote_received(doc, quote, user, supplier)" in send
	told = (tree.APP / "one" / "tell.py").read_text().split("def quote_received(", 1)[1]
	assert 'notify.notify(\n\t\t"Quote Received"' in told
	notes = tree.notifications()
	assert notes["Quote Received"]["module"] == notes["Quote Request Sent"]["module"] == "one_inventory"


def test_the_rest_of_the_portal_is_in_its_shell():
	"""An address and the profile are frappe's own web forms, read with its
	get_form_data and saved with its accept; a timesheet is listed once; a
	project's page is one_project/portal.page."""
	assert 'WEB_FORMS = {"profile": "edit-profile", "addresses": "addresses"}' in SOURCE
	assert "get_form_data(doctype, name, web_form)" in SOURCE
	assert "frappe.website.doctype.web_form.web_form.accept" in (APP / "src" / "parts" / "WebForm.vue").read_text()
	assert 'ADD = {"Address": ("addresses/new", _lt("Add Address"))}' in SOURCE
	assert "def _timesheet(" in SOURCE
	assert "onedesk.one_project.portal.page" in _page("Project.vue")


def test_the_account_pages_are_in_the_portals_shell():
	"""A portal reader's own pages are the sidebar's Account section (ACCOUNT):
	Profile, Password (frappe's update_password and its strength test), Your
	Data (the same calls as the desk's) and Third Party Apps once an app is let
	in. frappe's own pages of the same send a portal reader to them; a reset
	link keeps frappe's Set Password."""
	assert '("your-data", _lt("Your Data"), "shield-check")' in SOURCE
	assert '"OAuth Bearer Token"' in SOURCE and '"request-to-delete-data"' not in SOURCE
	assert '"target": "/your-data"' in HOOKS
	assert '"/portal/profile"' in (tree.APP / "www" / "me.py").read_text()
	password = _page("Password.vue")
	assert "frappe.core.doctype.user.user.update_password" in password and "test_password_strength" in password
	upw = (tree.APP / "www" / "update_password.py").read_text()
	assert 'not frappe.form_dict.get("key") and portal.reads()' in upw and '"/portal/password"' in upw
	assert '"/portal/apps"' in (tree.APP / "www" / "third_party_apps.py").read_text()
	data = _page("YourData.vue")
	for call in ("onedesk.one.privacy_copy.ask", "onedesk.one.privacy.ask_to_delete", "onedesk.one.privacy.withdraw"):
		assert call in data
	assert '"one_privacy"' in data
	privacy = (tree.APP / "one" / "privacy.py").read_text()
	told = (tree.APP / "one" / "tell.py").read_text()
	assert '"/portal/your-data"' in privacy and '"/your-data"' in privacy
	assert "link=privacy.where(doc.email)" in told and "link=privacy.where(user)" in told
	assert "frappe.www.third_party_apps.delete_client" in _page("Apps.vue")


def test_a_contact_is_invited_to_the_portal_by_one():
	"""frappe's Invite as User needs its System Manager, whom no workspace
	has: One's Invite to Portal is for an administrator or the party's
	manager, makes a Website User, links it without saving the whole party
	(and gives it the Customer or Supplier role erpnext would not), mails One's
	Portal Invitation with a week's link, and can be revoked and restored."""
	invite = (tree.APP / "one" / "portal_invite.py").read_text()
	assert 'MANAGERS = {"Customer": "Sales Manager", "Supplier": "Purchase Manager"}' in invite
	assert "clear_sessions(user=user, force=True)" in invite
	assert 'notify.mail("Portal Invitation", email, what=what, **said)' in (tree.APP / "one" / "tell.py").read_text()
	assert tree.notifications()["Portal Invitation"]["outside"]
	assert "row.db_insert()" in SOURCE and "user.add_roles(*sorted(missing))" in SOURCE and "party.save()" not in SOURCE
	js = (tree.APP / "public" / "js" / "contact.js").read_text()
	for verb in ("Invite to Portal", "Invite Again", "Revoke Access", "Restore Access"):
		assert f'__("{verb}")' in js
	assert '"Contact": "public/js/contact.js"' in (tree.APP / "hooks.py").read_text()
	home = (tree.APP / "one_admin" / "accounts.py").read_text()
	assert 'return "portal" if website else None' in home


def test_the_portal_says_what_the_reader_sees_once_and_plainly():
	for said in ('("Sales Order", "To Bill"): ("green", _lt("Delivered"))', '("Purchase Order", "To Receive"): ("amber", _lt("To deliver"))'):
		assert said in SOURCE, said
	assert r're.sub(r"\s*@\s*[\d.]+\s*$", "", tax.description' in SOURCE, "VAT 5% @ 5.0"
	assert "def number(" in SOURCE
	project = (tree.APP / "one_project" / "portal.py").read_text()
	assert "def progress(" in project and "def page(" in project
	assert "{_field(one, \"name\"): one for one in found}" in SOURCE, "a row counted once on Home"
