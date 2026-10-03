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
	Badge; and close to the edge on a phone."""
	head = (INCLUDES / "one_portal_head.html").read_text()
	assert 'class="one-avatar"' in head and 'href="/logout"' in head
	assert 'class="one-tab-buttons"' in head and '<use href="#icon-{{ tab.icon }}">' in head
	page = (tree.APP / "www" / "portal.html").read_text()
	assert "one_portal_columns(row_template)" in page and 'class="one-search"' in page
	css = (tree.APP / "public" / "css" / "portal.css").read_text()
	block = css.split("/* The portal a workspace's customers and suppliers sign in to (one/portal.py),", 1)[1]
	for token in ("var(--surface-gray-2)", "var(--ink-gray-5)", "var(--surface-amber-2)"):
		assert token in block
	assert "#" not in "".join(
		line for line in block.splitlines() if "color:" in line or "background:" in line
	)
	assert "padding: 1rem 0 3rem;" in block
	assert "ICONS = {" in SOURCE and "COLUMNS = {" in SOURCE
