"""The portal a workspace's customers and suppliers sign in to: a frappe-ui
app (frontend/portal) on frappe's own sidebar items and erpnext's own list
and page contexts, which one_portal/portal.py reads and answers as JSON."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

import tree

SOURCE = (tree.APP / "one_portal" / "portal.py").read_text()
HOOKS = (tree.APP / "hooks.py").read_text()
# What each module shows on the portal, in its own portal.py (the one_portal hook).
DECLARING = ("one", "one_crm", "one_inventory", "one_book", "one_project")
DECLARED = {folder: (tree.APP / folder / "portal.py").read_text() for folder in DECLARING}
SELLING, BUYING = DECLARED["one_crm"], DECLARED["one_inventory"]
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
	for gone in (
		"one_portal_head.html",
		"one_portal_sidebar.html",
		"transaction_row.html",
		"address_row.html",
	):
		assert not (includes / gone).exists(), gone
	assert not (tree.APP / "website").exists()
	redirects = HOOKS.split("website_redirects = [", 1)[1].split("\n]", 1)[0]
	for where in (
		'"target": r"/portal/\\1\\2"',
		'"/portal/projects"',
		'"/portal/addresses/\\1"',
		'"/portal/profile"',
	):
		assert where in redirects, where
	assert '{"source": r"/hrms(/.*)?", "target": "/desk/onehr"}' in redirects, "HRMS's phone app opens OneHR"
	assert "one_portal_" not in HOOKS


def test_the_tabs_are_portal_settings_by_role():
	assert "get_portal_sidebar_items()" in SOURCE
	assert 'OFF = ("/issues", "/material-requests")' in SOURCE
	assert '"/rfq": "Quote Requests"' in SOURCE
	assert '"onedesk.one_portal.portal.settle",' in HOOKS
	assert "onedesk.one.patches.portal_settle" in (tree.APP / "patches.txt").read_text()


def test_a_customers_or_suppliers_contact_is_a_portal_user():
	assert 'PARTIES = ("Customer", "Supplier")' in SOURCE
	assert '{"doctype": "Portal User", **where, "user": doc.user}' in SOURCE
	assert '"onedesk.one_portal.portal.invited"' in HOOKS.split('"Contact": {', 1)[1].split("},", 1)[0]


def test_the_portal_is_drawn_as_frappe_ui_draws_it():
	"""frappe-ui's DesktopShell with its Sidebar, or its MobileShell with a tab
	bar on a phone; each list frappe-ui's ListView, each page a PageHeader."""
	shell = (APP / "src" / "App.vue").read_text()
	assert "<DesktopShell" in shell and "<MobileShell" in shell and "<MobileNav" in shell
	assert "<Sidebar" in (APP / "src" / "parts" / "PortalSidebar.vue").read_text()
	assert "<PageHeader" in (APP / "src" / "parts" / "Head.vue").read_text()
	assert 'from "frappe-ui/list"' in _page("List.vue")
	assert all('"icon": "' in one for one in DECLARED.values()) and "COLUMNS = (" in SOURCE
	assert "portal.py" in (APP / "tailwind.config.js").read_text()


def test_a_record_page_is_the_portals():
	"""erpnext's record page context for the seven kinds first (the reader's
	permission, Pay), then the Badge, Download PDF, the facts, the items and
	the totals, answered by one_portal/portal.record."""
	record = (
		SOURCE.split("def record(", 1)[1].split("\ndef ", 1)[0]
		+ SOURCE.split("def _record(", 1)[1].split("\ndef ", 1)[0]
	)
	assert "from erpnext.templates.pages import order" in record and "_opened(doctype, name, order)" in record
	assert "frappe.utils.print_format.download_pdf" in record and "context.show_pay_button" in record
	assert "FACTS = (" in SOURCE and '"owed": True' in DECLARED["one_book"]
	assert '"terms": sanitize_html(doc.terms)' in SOURCE
	assert 'call("record"' in _page("Record.vue")


def test_a_supplier_answers_a_quote_request_on_the_portal():
	"""erpnext's request page context, which refuses a request not sent to the
	reader's supplier; the rows priced in place and sent through
	one_inventory/portal.send_quote, which reads everything but the rate, quantity and
	notes from the request itself, keeps the quote theirs, and tells the buyer."""
	rfq = BUYING.split("def rfq(", 1)[1].split("\ndef ", 1)[0]
	assert "from erpnext.templates.pages import rfq as page" in rfq and 'doc.get("rfq_links")' in rfq
	assert "send_quote" in _page("Rfq.vue")
	send = "".join(
		BUYING.split(f"def {one}(", 1)[1].split("\ndef ", 1)[0] for one in ("priced", "send_quote", "send")
	)
	assert '@frappe.whitelist(methods=["POST"])\ndef send_quote' in BUYING
	assert 'frappe.db.exists("Portal User", {"parent": supplier, "user": user})' in send
	assert "check_supplier_has_docname_access(supplier)" in send
	assert "for row in doc.items:" in send and "validate_existing_supplier_quotation" in send
	assert "finally:\n\t\tfrappe.session.user = user" in send
	assert 'quote.db_set({"owner": user, "modified_by": user}' in send
	assert "tell.quote_received(doc, quote, user, supplier)" in send
	assert "row.price_list_rate = rate" in send and "row.discount_percentage = discount" in send
	assert '"ignore_pricing_rule": 1' in send
	assert "def quote_preview(" in BUYING and "quote.calculate_taxes_and_totals()" in BUYING
	assert '"onedesk.one_inventory.portal.quote_preview"' in _page("Rfq.vue")
	told = (tree.APP / "one_inventory" / "tell.py").read_text().split("def quote_received(", 1)[1]
	assert 'notify.notify(\n\t\t"Quote Received"' in told
	notes = tree.notifications()
	assert notes["Quote Received"]["module"] == notes["Quote Request Sent"]["module"] == "one_inventory"


def test_the_rest_of_the_portal_is_in_its_shell():
	"""An address and the profile are frappe's own web forms, read with its
	get_form_data and saved with its accept; a timesheet is listed once; a
	project's page is one_project/portal.page."""
	assert 'WEB_FORMS = {"profile": "edit-profile", "addresses": "addresses"}' in SOURCE
	assert "get_form_data(doctype, name, web_form)" in SOURCE
	assert (
		"frappe.website.doctype.web_form.web_form.accept"
		in (APP / "src" / "parts" / "WebForm.vue").read_text()
	)
	assert '"add": ("addresses/new", _lt("Add Address"))' in DECLARED["one"]
	assert "def timesheet(" in DECLARED["one_project"]
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
	assert (
		"frappe.core.doctype.user.user.update_password" in password and "test_password_strength" in password
	)
	upw = (tree.APP / "www" / "update_password.py").read_text()
	assert 'not frappe.form_dict.get("key") and portal.reads()' in upw and '"/portal/password"' in upw
	assert '"/portal/apps"' in (tree.APP / "www" / "third_party_apps.py").read_text()
	data = _page("YourData.vue")
	for call in (
		"onedesk.one.privacy_copy.ask",
		"onedesk.one.privacy.ask_to_delete",
		"onedesk.one.privacy.withdraw",
	):
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
	Portal Invitation with a week's link, and can be revoked and restored, all
	from the one Portal dialog a contact, a customer, a supplier and a sent
	record open."""
	invite = (tree.APP / "one_portal" / "invite.py").read_text()
	assert 'MANAGERS = {"Customer": "Sales Manager", "Supplier": "Purchase Manager"}' in invite
	assert "clear_sessions(user=user, force=True)" in invite
	assert (
		'notify.mail("Portal Invitation", email, what=what, **said)'
		in (tree.APP / "one" / "tell.py").read_text()
	)
	assert tree.notifications()["Portal Invitation"]["outside"]
	assert (
		"row.db_insert()" in SOURCE
		and "user.add_roles(*sorted(missing))" in SOURCE
		and "party.save()" not in SOURCE
	)
	js = (tree.APP / "public" / "js" / "one_portal" / "portal.js").read_text()
	for verb in ("Invite", "Invite Again", "Revoke Access", "Restore"):
		assert f'__("{verb}")' in js
	for doctype in ("Contact", "Customer", "Supplier"):
		assert (
			f'onedesk.portal.open("{doctype}"'
			in js + (tree.APP / "public" / "js" / "one_portal" / "contact.js").read_text()
			or f'"{doctype}"' in js
		)
	assert '"Contact": "public/js/one_portal/contact.js"' in (tree.APP / "hooks.py").read_text()
	home = (tree.APP / "one_admin" / "accounts.py").read_text()
	assert 'return "portal" if website else None' in home


def test_the_portal_says_what_the_reader_sees_once_and_plainly():
	for said, where in (
		('"To Bill": ("green", _lt("Delivered"))', SELLING),
		('"To Receive": ("amber", _lt("To deliver"))', BUYING),
	):
		assert said in where, said
	assert r're.sub(r"\s*@\s*[\d.]+\s*$", "", tax.description' in SOURCE, "VAT 5% @ 5.0"
	assert "def number(" in SOURCE
	project = (tree.APP / "one_project" / "portal.py").read_text()
	assert "def progress(" in project and "def page(" in project
	assert '{_field(one, "name"): one for one in found}' in SOURCE, "a row counted once on Home"


def test_each_module_says_what_it_shows_on_the_portal():
	"""What a kind of record looks like on the portal is the module it belongs
	to's, in its own portal.py (one_portal/AGENTS.md): the engine keeps no
	table of anybody's records, each kind is declared once, and the hook names
	every module that declares."""
	import ast
	import re

	for table in ("ICONS", "TRANSACTIONS", "SAID_TO_READER", "CHAIN", "PARTY", "WAITING", "ASKS", "CALLED"):
		assert not re.search(rf"^{table} = ", SOURCE, re.M), f"{table} is a module's, in its own portal.py"
	hook = HOOKS.split("one_portal = [", 1)[1].split("]", 1)[0]
	seen = {}
	for folder, source in DECLARED.items():
		assert f'"onedesk.{folder}.portal"' in hook, f"the one_portal hook doesn't name {folder}"
		kinds = next(
			node.value
			for node in ast.parse(source).body
			if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "KINDS"
		)
		for name, one in zip(kinds.keys, kinds.values):
			keys = {key.value: value for key, value in zip(one.keys, one.values)}
			doctype = name.value
			assert doctype not in seen, f"{doctype} is declared by {seen[doctype]} and {folder}"
			seen[doctype] = folder
			assert "icon" in keys, f"{doctype} has no icon for its tab"
			if "transaction" in keys and "own_page" not in keys:
				assert "party" in keys and "steps" in keys, f"{doctype} lacks its party or its steps"
	assert set(seen) >= {
		"Quotation", "Sales Order", "Delivery Note", "Sales Invoice", "Request for Quotation",
		"Supplier Quotation", "Purchase Order", "Purchase Invoice", "Project", "Timesheet", "Address",
	}, sorted(seen)
