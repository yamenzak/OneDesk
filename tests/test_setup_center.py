"""SetupCenter (one/setup_center.py): each app's steps from what it declares,
done and waiting, and a step's form the wizard's own fields. Pure parts."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

from onedesk.one import setup_center, setup_steps

MAIL = (
	"OneMail",
	{
		"key": "domains",
		"title": "Your Company's Mail",
		"about": "Add the domain.",
		"tab": "setup",
		"fields": [{"fieldname": "domain", "fieldtype": "Data", "label": "Company Domain"}],
		"save": lambda values: None,
	},
)
TEMPLATES = ("OneMail", {"key": "templates", "title": "Mail Templates", "about": "Look them over.", "tab": "templates"})
PEOPLE = ("AccountCenter", {"key": "people", "title": "Invite Your People", "about": "Everybody.", "tab": "people"})
DECLARED = [PEOPLE, MAIL, TEMPLATES]


def _listed(off=(), may=lambda module, step: True, done=lambda module, step: False):
	return setup_center.sections(DECLARED, set(off), may, done)


def test_each_app_lists_its_steps_in_the_order_declared():
	said = _listed()
	assert [one["app"] for one in said] == ["AccountCenter", "OneMail"]
	assert [one["key"] for one in said[1]["steps"]] == ["domains", "templates"]
	assert [one["waiting"] for one in said] == [1, 2]


def test_done_and_waiting_come_from_the_step():
	said = _listed(done=lambda module, step: step["key"] != "templates")
	mail = said[1]
	assert [one["done"] for one in mail["steps"]] == [1, 0] and mail["waiting"] == 1
	assert all(one["waiting"] == 0 for one in _listed(done=lambda module, step: True))


def test_an_app_turned_off_or_a_step_the_reader_may_not_do_is_left_out():
	assert [one["app"] for one in _listed(off={"OneMail"})] == ["AccountCenter"]
	said = _listed(may=lambda module, step: step["key"] == "templates")
	assert [(one["app"], [s["key"] for s in one["steps"]]) for one in said] == [("OneMail", ["templates"])]


def test_a_step_with_fields_is_the_wizards_form():
	steps = _listed()[1]["steps"]
	assert steps[0]["fields"] == setup_steps.fields(MAIL[1], required=True)
	assert steps[0]["fields"][0]["fieldname"] == "domain" and steps[0]["fields"][0]["reqd"] == 1
	assert steps[1]["fields"] == []
	slide = setup_steps.fields(MAIL[1], "one_mail_domains_", required=False)
	assert slide[0]["fieldname"] == "one_mail_domains_domain" and slide[0]["reqd"] == 0
	check = {"fields": [{"fieldname": "allowed", "fieldtype": "Check", "label": "Allow"}]}
	assert setup_steps.fields(check, required=True)[0]["reqd"] == 0


def test_setupcenter_is_on_ones_rail_and_getting_started_opens_it():
	rail = json.loads((tree.APP / "one" / "sidebar" / "one" / "one.json").read_text())["items"]
	assert "/desk/one?center=setup" in {one.get("url") for one in rail}
	kit = (tree.APP / "public" / "js" / "one_interface" / "centre.js").read_text()
	assert 'onedesk.centers.open("setup", { at: module })' in kit and "getting_started = " not in kit
	market = (tree.APP / "one" / "marketplace.py").read_text()
	assert "center=setup&at=" in market, "Install in OneMarketplace lands on the app's steps"
