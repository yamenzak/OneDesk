"""The setup wizard's pure parts (one_admin/wizard_answers.py,
one/registry/fields.py and switches.py): what a field turns on, what an app
brings with it, which answers each step may keep, and which events are
noted."""

import pytest

from onedesk.one import setup_answers
from onedesk.one.registry import fields, switches
from onedesk.one_admin import wizard_answers as wizard


def test_every_field_turns_on_apps_that_are_switches():
	"""A field names only apps a workspace can turn on, and the answers'
	field is one of them."""
	ids = {one.id for one in switches.switches()}
	assert fields.unknown(ids) == []
	assert setup_answers.FIELDS == fields.IDS
	assert len(set(fields.IDS)) == len(fields.IDS)


def test_a_field_presets_its_own_apps_on_top_of_everyones():
	made = fields.preset("manufacturer")
	assert made[: len(fields.EVERY)] == fields.EVERY
	assert {"one_inventory", "one_factory", "one_quality"} <= set(made)
	assert fields.preset("other") == fields.EVERY
	assert fields.preset(None) == fields.EVERY
	assert "one_factory" not in fields.preset("services")


def test_an_app_brings_what_it_needs_however_far_down(monkeypatch):
	monkeypatch.setattr(switches, "_needs", lambda: {"factory": ("inventory",), "inventory": ("books",), "books": (), "deck": ()})
	on = switches.with_needs(["factory", "deck"])
	assert on == {"factory": (), "deck": (), "inventory": ("factory",), "books": ("factory",)}
	assert switches.needed_by("books", ["factory", "inventory", "books"]) == ("factory", "inventory")
	assert switches.needed_by("deck", ["factory", "deck"]) == ()


def test_the_answers_turn_on_what_a_chosen_app_needs(monkeypatch):
	monkeypatch.setattr(switches, "_needs", lambda: {"one_factory": ("one_inventory",)})
	said = switches.answer(["one_factory"])
	assert said["one_factory"] and said["one_inventory"]
	assert not said["one_crm"]
	assert "one" not in said, "an app always on is never a switch"


def test_a_step_keeps_only_its_own_answers():
	held = {"owner": {"email": "huda@example.com", "first_name": "Huda"}}
	kept = wizard.merge(held, "you", {"owner": {"first_name": "Hoda", "last_name": "K", "password": "x"}}, False)
	assert kept["owner"] == {"email": "huda@example.com", "first_name": "Hoda", "last_name": "K"}
	with pytest.raises(wizard.Refused):
		wizard.merge(held, "you", {"companies": []}, False)
	with pytest.raises(wizard.Refused):
		wizard.merge(held, "nowhere", {}, False)
	with pytest.raises(wizard.Refused, match="before payment"):
		wizard.merge(held, "company", {"companies": [{"name": "A", "country": "Oman"}]}, True)
	assert wizard.merge(held, "week", {"working_day": {"starts": "08:00", "ends": "17:00", "days_off": ["Friday"]}}, True)["working_day"]["days_off"] == ["Friday"]


def test_answers_kept_part_way_are_checked_as_far_as_they_go():
	held = {"owner": {"email": "huda@example.com", "first_name": "Huda"}}
	assert wizard.merge(held, "company", {"companies": [{"name": "Mansour Glass", "country": "United Arab Emirates"}]}, False)["companies"][0]["name"] == "Mansour Glass"
	with pytest.raises(setup_answers.Invalid) as wrong:
		wizard.merge(held, "field", {"field": "bakery"}, False)
	assert wrong.value.wrong[0].startswith("field ")
	with pytest.raises(setup_answers.Invalid):
		wizard.merge({"owner": {"email": "not an address", "first_name": "Huda"}}, "you", {"owner": {"first_name": "Huda"}}, False)
	with pytest.raises(setup_answers.Invalid):
		setup_answers.check(held)
	assert setup_answers.check(held, partial=True) == held


def test_a_company_may_name_its_group_among_the_answers():
	"""A company's parent is another company in the same answers, which the
	setup job makes a group; the demo's group answers check."""
	from onedesk.one_demo import group

	held = {"owner": {"email": "faisal@example.com", "first_name": "Faisal"}, "language": "en", "time_zone": "Asia/Dubai"}
	first = {"name": "Sahara Glass", "country": "United Arab Emirates", "parent": group.HOLDING}
	said = setup_answers.check({**held, "companies": [first, *group.answers()], "people": group.invited()})
	assert setup_answers.joined(said["companies"]) == [("Sahara Glass", group.HOLDING), *((one.name, group.HOLDING) for one in group.members())]
	assert all(one.answer(group.HOLDING)["chart"] == "Standard" for one in group.members())
	for parent in ("Sahara Glass", "Nowhere"):
		with pytest.raises(setup_answers.Invalid, match="is not another company"):
			setup_answers.check({**held, "companies": [{**first, "parent": parent}]})


def test_an_apps_steps_are_kept_one_by_one():
	held = {"owner": {"email": "huda@example.com", "first_name": "Huda"}, "steps": {"one_mail": {"private": {"allowed": 1}}}}
	kept = wizard.merge(held, "steps:one_mail.domains", {"steps": {"one_mail": {"domains": {"domain": "example.com"}}}}, True)
	assert kept["steps"] == {"one_mail": {"private": {"allowed": 1}, "domains": {"domain": "example.com"}}}
	with pytest.raises(wizard.Refused):
		wizard.kind("steps")
	assert wizard.kind("steps:one_mail.domains") == "steps"


def test_each_event_is_noted_once_and_left_only_while_open():
	rows = []
	assert wizard.noted(rows, "plan", "Reached")
	rows.append({"step": "plan", "event": "Reached"})
	assert not wizard.noted(rows, "plan", "Reached")
	assert wizard.noted(rows, "plan", "Left")
	rows.append({"step": "plan", "event": "Finished"})
	assert not wizard.noted(rows, "plan", "Left")
	assert not wizard.noted([], "plan", "Left")
	with pytest.raises(wizard.Refused):
		wizard.noted(rows, "plan", "Wandered")


def test_the_funnel_counts_how_far_each_signup_got():
	reached = lambda *steps: [{"step": one, "event": "Reached"} for one in steps]  # noqa: E731
	signups = [
		(reached("you"), False, False),
		(reached("you", "company", "apps"), False, False),
		(reached("you", "company", "apps", "plan", "payment"), True, False),
		(reached("you", "company", "steps:one_mail.domains", "people"), True, True),
		([], True, False),
	]
	funnel = {one["stage"]: one["signups"] for one in wizard.funnel(signups)}
	assert funnel["you"] == 5 and funnel["company"] == 4 and funnel["apps"] == 4 and funnel["plan"] == 3
	assert funnel["paid"] == 3 and funnel["people"] == 1 and funnel["live"] == 1
	assert [one["signups"] for one in wizard.funnel(signups)] == sorted([one["signups"] for one in wizard.funnel(signups)], reverse=True)
	stopped = {one["stage"]: one["signups"] for one in wizard.stopped(signups)}
	assert stopped["you"] == 1 and stopped["apps"] == 1 and sum(stopped.values()) == 2
	assert set(wizard.STAGES) <= set(wizard.STAGE_LABELS)
