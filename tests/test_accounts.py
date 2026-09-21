"""The two facts `docs/ACCOUNTS.md` turns on, read back from the checkout.

Payroll works out of the box because a Company with no chart chosen gets
ERPNext's generic "Standard" chart, and that is the only chart carrying the two
accounts HRMS looks up by name. Both halves of that are somebody else's code
and can change under us without a word, so both are asserted here rather than
only written down.
"""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CHARTS = Path(
	"/home/frappe/bench1/apps/erpnext/erpnext/accounts/doctype/account/chart_of_accounts/verified"
)

#: What `hrms.overrides.company.set_default_hr_accounts` searches for, by name.
WANTED = ("Payroll Payable", "Employee Advances")

sys.path.insert(0, str(ROOT / "scripts"))

import tree


@pytest.mark.skipif(not CHARTS.exists(), reason="no erpnext checkout on this box")
@pytest.mark.parametrize("chart", ("standard_chart_of_accounts.py", "standard_chart_of_accounts_with_account_number.py"))
def test_the_standard_chart_still_carries_the_hr_accounts(chart):
	"""Drop either of these from Standard and payroll breaks on a fresh site.

	Silently: nothing validates a default that was never set, so the first
	Payroll Entry is where it surfaces.
	"""
	text = (CHARTS / chart).read_text(encoding="utf-8")
	missing = [name for name in WANTED if name not in text]
	assert not missing, f"{chart} no longer has {missing}; see docs/ACCOUNTS.md"


@pytest.mark.skipif(not CHARTS.exists(), reason="no erpnext checkout on this box")
def test_the_country_charts_still_do_not():
	"""The reason onboarding must not default to a country chart.

	A country chart gaining both accounts would be good news and is allowed to
	fail this: it means docs/ACCOUNTS.md can stop saying "not one of them".
	"""
	carrying = []
	for path in sorted(CHARTS.glob("*.json")):
		text = path.read_text(encoding="utf-8")
		if all(name in text for name in WANTED):
			carrying.append(path.name)
	assert not carrying, (
		f"{carrying} now carry both HR accounts. Good news — update the counts in "
		"docs/ACCOUNTS.md and reconsider what onboarding should pick."
	)


#: Assigning this anywhere in our source is the mistake docs/ACCOUNTS.md exists
#: to stop: the country's chart looks like the thoughtful default and leaves
#: every payroll account empty. Both spellings — `x = "…"` in code and
#: `"chart_of_accounts": "…"` in a fixture.
FORBIDDEN = re.compile(r"""chart_of_accounts"?\s*[:=]\s*['"]""")


def test_we_never_choose_a_chart_of_accounts():
	guilty = [
		str(path.relative_to(ROOT))
		for path in tree.sources() + tree.fixtures()
		if FORBIDDEN.search(path.read_text(encoding="utf-8"))
	]
	assert not guilty, (
		f"{guilty} sets chart_of_accounts. Leaving it empty is what makes payroll "
		"work out of the box; see docs/ACCOUNTS.md."
	)
