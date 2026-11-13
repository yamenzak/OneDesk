"""Companies in AccountCenter (account_center/companies.py) and what makes a
company after the first ready to pay and invoice (one/companies.py). Pure
parts, and who may."""

import ast
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SCREEN = tree.APP / "account_center" / "companies.py"
READY = tree.APP / "one" / "companies.py"
JOB = tree.APP / "one" / "setup_job.py"


class _Answers:
	CHARTS = ("Standard", "Standard with Numbers")


def _load(path, names, **space):
	space = {"_": lambda s: s, "date": date, **space}
	for node in ast.parse(path.read_text()).body:
		named = getattr(node, "name", None) or (getattr(node.targets[0], "id", None) if isinstance(node, ast.Assign) else None)
		if named in names:
			exec(ast.unparse(node), space)
	return space


R = _load(READY, {"LETTER_HEADS", "starts_of", "year_name"})
S = _load(SCREEN, {"asked", "rows"}, setup_answers=_Answers, LETTER_HEADS=R["LETTER_HEADS"])


def test_a_company_is_asked_its_name_country_and_one_of_the_two_charts():
	asked = S["asked"]
	assert asked("  Sahara   Riyadh ", "Saudi Arabia", None, None, None) == {
		"name": "Sahara Riyadh",
		"country": "Saudi Arabia",
		"chart": "Standard",
		"letter_head": "own",
	}
	said = asked("Sahara Riyadh", "Saudi Arabia", "SAR", "Standard with Numbers", "first")
	assert said["currency"] == "SAR" and said["chart"] == "Standard with Numbers" and said["letter_head"] == "first"
	for wrong in (("", "Saudi Arabia", None, None, None), ("A", "", None, None, None), ("A", "Germany", None, "SKR04", None), ("A", "Germany", None, None, "theirs")):
		with pytest.raises(ValueError):
			asked(*wrong)


def test_the_default_company_is_listed_first():
	listed = S["rows"]([{"name": "beta"}, {"name": "Alpha"}, {"name": "Main"}], "Main")
	assert [one["name"] for one in listed] == ["Main", "Alpha", "beta"]
	assert [one["default"] for one in listed] == [True, False, False]


def test_a_financial_year_is_named_as_erpnexts_wizard_names_it():
	name = R["year_name"]
	assert name(date(2026, 1, 1), date(2026, 12, 31), "SCR") == "2026"
	assert name(date(2026, 4, 1), date(2027, 3, 31), "SCR") == "2026-2027"
	assert name(date(2026, 1, 1), date(2026, 12, 31), "SCR", {"2026"}) == "2026 SCR"
	assert R["starts_of"](date(2026, 4, 1)) == "04-01" and R["starts_of"](None) is None


def test_the_screen_and_the_setup_job_make_a_company_through_one_function():
	job = JOB.read_text()
	body = job.split("def company(", 1)[1].split("\ndef ", 1)[0]
	assert "from onedesk.one.companies import ready" in body and "ready(doc.name, said, days_off)" in body
	assert "setup_wizard.holiday_list" not in body, "the holiday list is companies.ready's"
	screen = SCREEN.read_text()
	assert "setup_job.company(said)" in screen and 'frappe.get_doc(\n\t\t{\n\t\t\t"doctype": "Company"' not in screen


def test_only_an_administrator_adds_a_company():
	screen = SCREEN.read_text()
	for name in ("make", "currency"):
		body = screen.split(f"def {name}(", 1)[1].split("\n@frappe.whitelist", 1)[0]
		assert body.index("roles.require()") < body.index("return"), name
	center = (tree.APP / "account_center" / "center.py").read_text()
	assert '("companies", _lt("Companies"), "building-2", "workspace")' in center


def test_what_a_second_company_needs_is_done_for_it():
	ready = READY.read_text().split("def ready(", 1)[1].split("\ndef ", 1)[0]
	for part in ("_year(", "setup_wizard.holiday_list(", "periods.make(", "_components(", "_letter_head("):
		assert part in ready, part
