"""The setup wizard, read back without a site: who can open it, what it picks
for somebody who changes nothing, and what it leaves for next year.
"""

from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "onedesk"
WIZARD = (APP / "one" / "setup_wizard.py").read_text()
SLIDES = (APP / "public" / "js" / "setup_wizard.js").read_text()


def test_the_owner_can_open_the_wizard():
	"""Nobody on a workspace has System Manager, the only role frappe's page
	allows, and the router sends everybody to it until setup is done."""
	source = (APP / "one" / "access.py").read_text()
	pages = source.split("PAGES = ", 1)[1].split("\n", 1)[0]
	assert '"setup-wizard"' in pages


def test_the_standard_chart_is_the_one_picked():
	"""No national chart carries both payroll accounts (docs/ACCOUNTS.md)."""
	assert '["Standard", ...r.message.filter((one) => one !== "Standard")]' in SLIDES
	assert 'set_value("Standard")' in SLIDES


def test_the_days_off_are_the_countrys_and_can_be_two():
	assert 'fieldtype: "MultiCheck"' in SLIDES
	assert "frappe.boot.one_weekends" in SLIDES
	assert "country_holidays" in WIZARD and ".weekend" in WIZARD
	assert "one_weekends" in (APP / "one" / "boot.py").read_text()


def test_the_leave_and_payroll_years_are_the_companys():
	"""The fiscal year the wizard was told, not January, and the next one is
	made before this one runs out."""
	assert 'args["fy_start_date"]' in WIZARD
	assert "-01-01" not in WIZARD
	periods = (APP / "one_hr" / "periods.py").read_text()
	assert "get_fiscal_year" in periods
	assert '"onedesk.one_hr.periods.daily"' in (APP / "hooks.py").read_text()


def test_one_failing_settle_does_not_undo_the_setup():
	settle = WIZARD.split("def settle", 1)[1].split("\ndef ", 1)[0]
	assert "savepoint" in settle and "log_error" in settle
