"""The setup job without a site: what answers it refuses, what it hands
frappe's wizard, and that a run after a failure goes on where it stopped."""

from datetime import date

import pytest

from onedesk.one import setup_answers, setup_job

GOOD = {
	"owner": {"email": "layla@example.com", "first_name": "Layla"},
	"language": "en",
	"time_zone": "Asia/Dubai",
	"companies": [{"name": "Sahara Glass", "country": "United Arab Emirates"}],
}


def _refused(answers: dict) -> str:
	with pytest.raises(setup_answers.Invalid) as raised:
		setup_answers.check(answers)
	return str(raised.value)


def test_the_least_answers_are_enough():
	assert setup_answers.check(dict(GOOD)) == GOOD


def test_what_is_missing_is_named():
	said = _refused({"owner": {"email": "layla@example.com"}})
	for missing in ("language is missing", "time_zone is missing", "companies is missing", "owner.first_name is missing"):
		assert missing in said


def test_an_unknown_key_is_refused_at_every_level():
	said = _refused({**GOOD, "colour": "blue", "owner": {**GOOD["owner"], "phone": "1"}, "companies": [{**GOOD["companies"][0], "vat": "x"}]})
	assert "unknown key 'colour'" in said
	assert "owner has an unknown key 'phone'" in said
	assert "companies[0] has an unknown key 'vat'" in said


def test_a_countrys_own_chart_is_refused():
	said = _refused({**GOOD, "companies": [{**GOOD["companies"][0], "chart": "Germany - SKR04"}]})
	assert "ACCOUNTS.md" in said
	assert setup_answers.check({**GOOD, "companies": [{**GOOD["companies"][0], "chart": "Standard with Numbers"}]})


def test_wrong_answers_are_each_said():
	said = _refused(
		{
			**GOOD,
			"time_zone": "Mars/Olympus",
			"field": "piracy",
			"working_day": {"starts": "25:00", "ends": "17:00", "days_off": ["Funday"]},
			"apps": {"one_nothing": False},
			"people": [{"email": "not an address", "first_name": "Omar", "levels": {"one_nothing": "User"}}],
		}
	)
	for wrong in ("Mars/Olympus", "piracy", "working_day.starts", "days_off", "one_nothing", "people[0].email"):
		assert wrong in said


def test_a_kept_app_cannot_be_turned_off():
	assert "apps.one is kept and can't be turned off" in _refused({**GOOD, "apps": {"one": False}})


def test_the_wizard_is_given_the_first_company_and_never_a_user():
	said = setup_answers.wizard(
		{**GOOD, "working_day": {"starts": "8:00", "ends": "17:00", "days_off": ["Sunday"]}}, "AED", "English", date(2026, 11, 13)
	)
	assert said["company_name"] == "Sahara Glass" and said["company_abbr"] == "SG"
	assert (said["fy_start_date"], said["fy_end_date"]) == ("2026-01-01", "2026-12-31")
	assert said["onedesk_day_starts"] == "08:00:00" and said["onedesk_weekly_off"] == ["Sunday"]
	assert "email" not in said and "full_name" not in said and "chart_of_accounts" not in said


def test_the_year_is_the_one_today_is_in():
	assert setup_answers.fiscal_year("04-01", date(2026, 2, 1)) == (date(2025, 4, 1), date(2026, 3, 31))
	assert setup_answers.fiscal_year("04-01", date(2026, 4, 1)) == (date(2026, 4, 1), date(2027, 3, 31))


def test_a_short_name_taken_gets_a_number():
	assert setup_answers.abbreviation("Sahara Glass & Aluminium") == "SGA"
	assert setup_answers.abbreviation("Sahara Glass", {"SG", "SG2"}) == "SG3"


def test_the_countrys_number_format_has_decimals():
	assert setup_answers.number_format("#.###") == "#.###,##"
	assert setup_answers.number_format("#,###") == "#,###.##"
	assert setup_answers.number_format("#'###.##") == "#'###.##"


def test_apps_answered_move_only_their_own_rows():
	from onedesk.one import registry

	crm = registry.get("one_crm").sidebar
	assert setup_answers.switched(GOOD, ["Other"]) is None
	assert setup_answers.switched({**GOOD, "apps": {"one_crm": False}}, ["Other"]) == sorted(["Other", crm])
	assert setup_answers.switched({**GOOD, "apps": {"one_crm": True}}, ["Other", crm]) == ["Other"]


def _steps(ran: list, failing: str | None = None) -> dict:
	def step(name):
		def run(_answers):
			if name == failing:
				raise RuntimeError("no")
			ran.append(name)

		return run

	return {name: step(name) for name in setup_job.ORDER}


def test_the_steps_run_in_order_once():
	ran, kept = [], []
	held = setup_job.walk(GOOD, _steps(ran), {}, lambda said, failed: kept.append((list(said["done"]), failed)))
	assert ran == list(setup_job.ORDER) == held["done"]
	assert kept[-1] == (list(setup_job.ORDER), False)
	again = []
	setup_job.walk(GOOD, _steps(again), held, lambda *_, **__: None)
	assert again == []


def test_a_run_after_a_failure_goes_on_from_the_step_that_failed():
	ran, kept = [], []
	with pytest.raises(RuntimeError):
		setup_job.walk(GOOD, _steps(ran, failing="companies"), {}, lambda said, failed: kept.append(dict(said, failed_now=failed)))
	assert ran == ["settings", "wizard", "owner"]
	assert kept[-1]["failed"].startswith("companies") and kept[-1]["failed_now"]
	more = []
	held = setup_job.walk(GOOD, _steps(more), kept[-1], lambda *_, **__: None)
	assert more == ["companies", "apps", "steps", "people"]
	assert held["failed"] is None


def test_every_step_has_its_function():
	assert set(setup_job.STEPS) == set(setup_job.ORDER)
