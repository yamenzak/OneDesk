"""A crumb leads back where the reader came from, as the rail names it
(one/homes.py, one/titles.py, public/js/shell.js), and a rail row filters
only its own list."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SHELL = (tree.APP / "public" / "js" / "shell.js").read_text()
REPORTS = (tree.APP / "public" / "js" / "reports.js").read_text()
HOOKS = (tree.APP / "hooks.py").read_text()


def _rows():
	for path in sorted(tree.APP.glob("*/sidebar/*/*.json")):
		for row in json.loads(path.read_text()).get("items") or []:
			yield path, row


def test_a_rail_row_filters_only_its_own_list():
	for path, row in _rows():
		if row.get("link_type") != "DocType" or not row.get("filters"):
			continue
		for one in json.loads(row["filters"]):
			if isinstance(one, list) and len(one) == 4:
				assert one[0] == row["link_to"], f"{path.parent.name}: {row['label']} filters {one[0]}"


def test_a_crumb_says_what_the_rail_says_and_leads_home():
	assert "List.prototype.get_breadcrumbs = function" in SHELL
	assert "frappe.ui.form.get_breadcrumbs = function (frm)" in SHELL
	assert "frappe.boot.one_homes" in SHELL and ".Crumb" in SHELL
	assert "Sidebar.prototype.find_active_item = function" in SHELL
	assert "frappe.breadcrumbs" not in REPORTS and "BaseList.prototype.get_breadcrumbs" in REPORTS
	assert "TreeView.prototype.set_title" in REPORTS and "crumb(this.doctype)" in REPORTS
	assert 'one_homes = ["onedesk.one.masters.homes", "onedesk.one_project.rates.homes"]' in HOOKS
	titles = (tree.APP / "one" / "titles.py").read_text()
	assert 'found["Crumb"]' in titles and "len(labels) == 1" in titles
	masters = (tree.APP / "one" / "masters.py").read_text()
	assert 'f"/desk/masters?type={doctype}"' in masters.split("def homes(", 1)[1].split("\ndef ", 1)[0]


def test_a_folded_group_opens_around_the_page_it_holds():
	assert "Sidebar.prototype.find_active_item = function" in SHELL
	assert "sidebar.active_item = $row" in SHELL
