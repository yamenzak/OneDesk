# Where a company's accounts come from

Written by hand, and measured rather than assumed. Counts are against the
ERPNext and HRMS shas in `upstream.json`; `tests/test_accounts.py` reads the
two facts this turns on back from the checkout.

We add nothing to this. No account, no chart, no default — onedesk's source
contains no assignment to `chart_of_accounts` and no code that creates an
Account, and there is a guard that keeps it that way. Everything below is
ERPNext's and HRMS's own behaviour, written down because it is the opposite of
what it looks like.

## What happens today

Creating a Company builds its whole chart of accounts. Nobody types an account
number, which is the behaviour we want and already have.

HRMS then runs `set_default_hr_accounts` on that same company
(`hrms/overrides/company.py`) and fills two fields by looking the accounts up
**by name**:

    default_payroll_payable_account   ← the account named "Payroll Payable"
    default_employee_advance_account  ← the account named "Employee Advances"

`set_expense_claim_type_accounts` wires every Expense Claim Type the same way.
From then on the per-employee fields are overrides nobody has to fill: an
Employee Advance with no account falls back to the company's
(`employee_advance.py`, `before_submit`), and a Salary Structure Assignment
with no cost centre falls back to the department's
(`salary_structure_assignment.get_payroll_cost_center`).

## The part that is backwards

Which chart gets built depends on `Company.chart_of_accounts`. Leave it empty
and `company.py` sets it to **"Standard"** — ERPNext's generic chart, not the
country's.

That fallback is the only reason any of the above works.

    Standard chart                      Payroll Payable ✓   Employee Advances ✓
    Standard with Numbers               Payroll Payable ✓   Employee Advances ✓
    72 country charts                   Payroll Payable 3   Employee Advances 0
                                        with both: 0

Not one of the seventy-two national charts carries both accounts. Three carry
"Payroll Payable" (India, and two Singapore charts) and none of those carry
"Employee Advances". So a company created on its own country's chart gets
neither default filled, nothing complains at setup — `validate_default_accounts`
only checks an account that is already set — and the first Payroll Entry is
where somebody finds out.

**So do not default onboarding to the country's chart.** The instinct is
obvious and it breaks payroll in every country. Leaving the field alone is the
correct behaviour, not an oversight.

## If a customer needs their national chart

Some will: an accountant in Germany expects SKR03 or SKR04, and a generic chart
is not something they can file from. The fix is not to change the default. It
is to create the two accounts under whichever chart was built, after it is
built, and let `set_default_hr_accounts` find them — about twenty lines against
a `Company` `after_insert`, and a decision per country about which parent they
hang under.

Nothing here wants OneAI. Choosing a ledger account is a fixed mapping whose
wrong answers end up in a tax filing, and a guess that is right most of the
time is worse than a field somebody fills in once.
