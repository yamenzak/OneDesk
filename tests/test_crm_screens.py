"""What OneCRM's screens show and leave out, and why each stays that way."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

CRM = tree.APP / "one_crm"


def _setters(name):
	return json.loads((CRM / "custom" / f"{name}.json").read_text())["property_setters"]


def test_the_rail_offers_no_report_one_has_replaced():
	declutter = (tree.APP / "one" / "declutter.py").read_text(encoding="utf-8")
	rail = json.loads((CRM / "sidebar" / "onecrm" / "onecrm.json").read_text())["items"]
	for item in rail:
		if item.get("link_type") == "Report":
			assert f'"{item["link_to"]}"' not in declutter, f"{item['label']} is disabled"


def test_the_setting_capture_depends_on_cannot_be_unticked():
	"""Unticking it brings back erpnext's refusal of the web form and the inbox."""
	hidden = {row["field_name"] for row in _setters("crm_settings") if row["property"] == "hidden"}
	assert "allow_lead_duplication_based_on_emails" in hidden


def test_a_lead_and_a_deal_are_linked_by_name():
	for name in ("lead", "opportunity"):
		shown = {row["property"]: row["value"] for row in _setters(name) if row["doctype_or_field"] == "DocType"}
		assert shown.get("show_title_field_in_link") == "1", name


def test_where_a_lead_came_from_is_open_on_the_form():
	for name in ("lead", "opportunity"):
		section = {row["property"]: row["value"] for row in _setters(name) if row.get("field_name") == "utm_analytics_section"}
		assert section.get("collapsible") == "0", name
	assert "enable_utm = 1" in (CRM / "capture.py").read_text(encoding="utf-8")


def test_access_is_changed_once_and_on_both_paths():
	hooks = (tree.APP / "hooks.py").read_text(encoding="utf-8")
	assert hooks.count('"onedesk.one_crm.access.settle"') == 2, "after install and after migrate"
	source = (CRM / "access.py").read_text(encoding="utf-8")
	assert 'frappe.db.exists("Custom DocPerm", {"parent": doctype})' in source, "a workspace's own decision stands"
