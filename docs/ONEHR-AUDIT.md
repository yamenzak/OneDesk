# OneHR, screen by screen

Written by hand, one entry per rail row, as the walk reaches it. Each entry says
what was wrong, what was done, and what was deliberately left.

The Time group was walked first and its entries live in `docs/ATTENDANCE.md`,
which is the plan for that arc rather than an audit. Everything from Leave
onwards is here.

Three faults recur often enough to be worth naming once:

- **A screen asks which company.** One workspace is one company. The doctype
  fields are swept by `one/company.py`; report filters are swept in
  `public/js/reports.js`, because a report's filters are a list in its own
  script rather than doctype fields.
- **A report builds its rows from the records that exist and calls the result a
  measurement.** All three Time reports did this, and it is the difference
  between "nobody was late" and "twenty-six days were never counted".
- **A request is answered by setting a dropdown and pressing Submit**, with
  nothing recording who decided or why, and `on_submit` throwing if the dropdown
  was not set first — a rule the toolbar button does not carry.

## Sweeps

**Company off every report filter** — `a871ec9`. Seventeen reports in the OneHR
rail asked which company. `public/js/reports.js` fills the filter from the site
and hides it after `setup_filters` has built it, so nothing downstream changes.

**A report is called what the rail called it** — `c96596e`. Five rail rows
opened a page with a different name at the top. The rail's own labels come down
in the boot from `one/titles.py`, read from the Sidebar rows rather than typed
into a list. Dashboards disagree too — Payroll Overview opens "Payroll",
Expense Overview opens "Expense Claims", Overview opens "Human Resource",
Recruitment Overview opens "Recruitment", Lifecycle Overview opens "Employee
Lifecycle". **Closed during the Pay walk**: a dashboard's heading is the last
crumb too, but `Dashboard.set_breadcrumbs` passes only
`{module, doctype, docname}` while `set_dashboard_breadcrumb` beside it reads a
`label` its own caller never sends. So `frappe.breadcrumbs.add` is wrapped and
the crumb is labelled on its way through. The browser tab is left as it is:
`Dashboard.show` calls `set_title` a line after the crumb, and a tab reading
"Payroll Dashboard" beside a page reading "Payroll Overview" is not worth a
second patch.

## Leave

### Leave Application

Found:

1. Two headlines stacked — frappe's "Submit this document to confirm" and
   HRMS's "Submit this Leave Application to confirm." — and neither says what
   approving does.
2. No Approve or Reject. The verdict is a Status dropdown the approver edits by
   hand, and `on_submit` throws "Only Leave Applications with status 'Approved'
   and 'Rejected' can be submitted" if they forget. Third request doctype in
   OneHR, third approval shape.
3. Nothing records who decided, when, or why.
4. `Follow via Email` — a mail preference on a leave form.
5. `Posting Date` editable, though it is the day the application was made.
6. `Leave Approver Name` beside `Leave Approver`, saying the same thing twice.
7. The Allocated Leaves table reads **Available Leaves 21** beside **Leaves
   Pending Approval 3**, and the 3 is the application being read.

Done: the same two buttons, note dialog and three signed fields as Attendance
Request and Shift Request, out of `one_hr/decision.py`. Status is read-only
because the buttons set it, and `before_submit` reads a plain Submit as a yes.
One headline, saying what approving books and what it leaves: *Approving this
books 3 days of Annual Leave for Rania Sabbagh, 01-10-2026 to 03-10-2026,
leaving them 18.* The balance is worked out with HRMS's own
`get_leave_balance_on` rather than read off `leave_balance`, which is filled by
their form script and stays at nought on an application created any other way —
it read 0 against an allocation of 21. Follow via Email and Leave Approver Name
hidden; Posting Date read-only and relabelled *Asked For On*.

Left: the Allocated Leaves table itself is rendered by HRMS's own form script
and still counts this application as pending rather than spent. The headline
answers the question it raises; rewriting the table would mean owning their
render.

**The two mails now have something to send.** HRMS ships
`send_leave_notification` on and no template, so every approval printed *"Please
set default template for Leave Status Notification in HR Settings."* — the
product promising an email it could not deliver. `fixtures/email_template.json`
carries Leave Approval Notification and Leave Status Notification, and
`leave.templates()` points the two settings at them on migrate, only where a
workspace has not chosen its own. The note somebody types into the Reject dialog
reaches the person, because `one_note` is a field like any other in the template
context. Rendered against the real record they read *"Rania Sabbagh has asked
for 3 days of Annual Leave"* and *"Your Annual Leave request was approved"*.
Their content is English only for now.

**And the screen went quiet.** From the second leave application onwards, every
approval also said *"HR Telemetry Milestone first_leave_applied already
exists"*. HRMS counts first-time milestones by inserting a row inside
`savepoint(catch=Exception)` and letting the unique index refuse the second
attempt — the row rolls back, the message does not, because
`frappe.local.message_log` is a list on the request rather than part of the
transaction. The same message lands on expense claims, attendance requests,
shift requests, job offers, appraisals, interviews, payroll entries and salary
slips. `one/quiet.py` is hooked on `"*"` for the two events their telemetry
attaches to and drops only messages naming that doctype.

### Leave Allocation

Found:

1. The list is about a number of days and does not say one. Employee Name,
   Status, **Employee**, Leave Type, ID — three rows all reading *Rania
   Sabbagh · Submitted · HR-EMP-00001*, and the 7, the 10 and the 21 nowhere.
2. `Employee Name: Rania Sabbagh` sitting under `Employee: HR-EMP-00001: Rania
   Sabbagh`, which is the same sentence twice.
3. `New Leaves Allocated` reads **7.000** and `Total Leaves Allocated`, directly
   beneath it, reads **7**.
4. Nothing says what Total Leaves Allocated is or that it is worked out on save.

Done: `total_leaves_allocated` and `from_date` join the list and `employee`
leaves it, so a row reads *Tarek Nassar · Submitted · Annual Leave · 01-01-2026
· 21*. Both leave Floats get a precision of 2 rather than the site's 3, which
is what a day counted in halves and quarters needs. Descriptions on the two
allocation fields.

Left: `7.00` in the input and `7` in the read-only field still disagree, because
frappe's Float formatter drops the decimals of a whole number (`formatters.js`,
"show 1.000000 as 1") and the Data control's `format_for_input` does not. That
is a framework-wide difference and not this screen's to settle.

**`total_leaves_allocated` is already `read_only` upstream.** A property setter
restating that was written and then removed: a customization that agrees with
the thing it customizes is noise, and it would hide the day upstream changed
its mind.

### An employee link reads the person's name

The mirror field is the finding that recurs everywhere, so it is answered once.

Employee has a title field and `show_title_field_in_link` off, so every link to
it read `HR-EMP-00004` and erpnext's answer, on doctype after doctype, was a
read-only `Employee Name` hung beside the link and fetched from the same record.
Fifty-four doctypes carry one.

Turning the switch on is one property setter in `one_hr/custom/employee.json`,
and it reaches further than the form: the list, the grid, the link dropdown and
the printed document all read the title, because print resolves it through
`__link_titles` in `frappe/www/printview.py` by the same rule. So the mirrors
have nothing left to say, and `one_hr/names.py` hides the forty-seven of them
that are literally `fetch_from: employee.employee_name` — a mirror by
definition. Parent doctypes only: in a grid the mirror *is* the column somebody
reads. And only where `employee_name` is the doctype's title field or is not in
the list view, because a list's title column is drawn from `title_field` rather
than from the field being visible, so hiding it there costs nothing — `Goal` is
the one row where it would have cost the name, and it is left alone.

### Leave Policy Assignment

Found: `Leave Policy` read `HR-LPOL-2026-00001` and `Leave Period` read
`HR-LPR-2026-00001`. Neither is a name, and choosing between two policies by
serial is not choosing. The list repeated the employee id beside the employee
name, and did not say when the assignment starts.

Done: Leave Policy gets `show_title_field_in_link`, so it reads **Standard**.
Leave Period has no title field to show, so `setup_wizard._leave_period` renames
the one it creates to its year — the link, and three report filters, now read
**2026**. `effective_from` joins the list and `employee` leaves it.

### The leave year

There was no `Leave Period` on the site, and nothing in HRMS creates one.
`Employee Leave Balance` asks `get_leave_period` for the dates to run between,
gets `None`, and its `onload` dies on `data.message[0]` — so both mandatory date
filters stay empty, the report shows nothing, and no part of the screen says
why. Leave Policy Assignment and the two allocation tools want one too.

Done: `set_the_working_day` creates the calendar year alongside the holiday list
and the shift, named for its year. The report returns 42 rows where it returned
none. The calendar year rather than a financial one, because a leave year that
is not the calendar year is a decision a workspace makes deliberately.

**`standard_working_hours` is 8.5 on this site and that is correct** — it is
`set_the_working_day` reading back the working day the wizard was told, not
HRMS's default leaking through. Flagged during the Time walk as a possible
defect; it is not one.

### Leave Balance, Leave Balance Summary

Both work and both say something. The only fault was **Employee and Employee
Name as two columns reading "Samir Aoun | Samir Aoun"** — the report version of
the mirror field, and neither `names.py` nor `company.py` can reach it, because
a report's columns are a list built in Python in another app. So
`public/js/reports.js` drops an `employee_name` column wherever an Employee Link
column is present in the same report, and only then: a report that shows the
name and not the link still shows the name.

Left: a report Float reads **21.000**. Frappe formats every report cell with
`always_show_decimals: true` at the site's float precision of three, so a day
count and a currency amount are shown the same way. Changing that is a site-wide
decision and payroll is the other half of it.

### Working on a Holiday

The screen said **Nothing to show** while six days of it existed. Not a defect
in the report: Rania had a `Holiday List Assignment` of her own, against a
"One Holidays 2026" list of 52 Sundays that nothing in this app creates, while
everybody else was on the company's "One 2026" of Fridays and national days. She
worked six Fridays, and none of them was a holiday *of her list*. Dev-site dirt
from an earlier run with a different weekly off; the stray assignment and list
were removed and the report answers 14 rows.

Worth saying once because it is the shape of a real support call: **an employee
may carry a holiday list that disagrees with the company's, and no screen says
so.** The report is right and looks broken.

### Leave Control Panel

Found:

1. It opens saying it will allocate **from today until nothing**.
   `set_leave_details` sets `dates_based_on: "Leave Period"`, a leave period,
   and `from_date: today, to_date: null` in the same `set_value`. The dates are
   meant to arrive from the period by `add_fetch`, which fires when somebody
   *changes* the period — and nobody changes a field that is already filled.
2. A **Company** column in the employee table, the same company on every row.
   The doctype's own field is hidden by `one/company.py`, but this table is a
   datatable built in their form script, so it is not a field.
3. **Leave Policy** is mandatory and deliberately cleared, so the form opens
   with a red box before anybody has done anything wrong.

Done: our own form script fills the dates from the period on load and on every
change of either; drops the Company column by replacing
`get_employees_datatable_columns`; and fills Leave Policy when the workspace has
written exactly one. The panel now opens as *Standard · 2026 · 01-01-2026 to
31-12-2026*, ready to allocate.

Two things about frappe's form scripts that this turned on, and that are worth
knowing before writing the next one: **field handlers are a list** — ours runs
alongside theirs, so their `leave_policy` handler still refreshes the employee
table — while **`frm.events.X` is a slot** holding the last registered, which is
what lets `get_employees_datatable_columns` be replaced rather than wrapped. And
a `set_value` of a whole object applies in key order with awaits between, so
anything written from a trigger fired part-way through is overwritten by the
rest of the batch. Filling the policy is hung on the clearing of the policy
itself, which is the last word either way.

### Leave Encashment

The screen could not be used at all, in two places, and neither said so until
Submit.

1. **The leave type had nothing to pay with.** HRMS's own setup ships Casual
   Leave with `allow_encashment: 1` and no `earning_component`, and
   `create_additional_salary` throws *"Please set Earning Component for Leave
   type"* on submit — after the form has been filled in. `leave.encashable()`
   points every encashable leave type that has none at HRMS's own **Leave
   Encashment** salary component, which their payroll data installs. Only a
   leave type that has none is touched, and if the component is not on the site
   nothing happens and the throw stands, because there is nothing to point at.
2. **The amount was 0.00 and the form did not say why.** HRMS reads the rate
   from `leave_encashment_amount_per_day` on the Salary Structure Assignment, or
   failing that the Salary Structure. Nothing fills it and nothing asks for it,
   so every encashment read nought and `before_submit` answered *"You can only
   submit Leave Encashment for a valid encashment amount"* — a sentence naming
   neither the field nor where it lives. Now the record says it first: *Nothing
   to pay yet: One Monthly has no Leave Encashment Amount Per Day, so a day is
   worth nought. Set it on the salary structure or on this person's assignment.*
   And once there is a rate: *Submitting this pays Lina Farah د.إ 700.00 for 7
   days of Casual Leave.*

**Deriving a rate was considered and rejected.** A day's pay is `base / working
days` or `base / 30` or the basic component alone depending on the contract and
the country. A product that guesses pays somebody the wrong amount without being
asked, and the two numbers it would be guessed from are both on the screen
already.

Also: the three day counts read 7, 7.000 and 7 — precision 2 on all three; the
Status field repeated the header's own Draft pill and is hidden; and Currency
sat beside an amount already formatted in it.

## Pay

### A payroll run could not be made at all

ERPNext's standard chart of accounts creates **Payroll Payable** under Accounts
Payable with an `account_category` and no `account_type`, and nominates it as
the company's `default_payroll_payable_account`. HRMS's Payroll Entry then
refuses: *"Account type should be set **Payable** for payroll payable account
**Payroll Payable - ONE**, please set and try again"*. So out of the box the
account exists, the payroll entry is pointed at it, and the run cannot be made
until somebody who knows what `account_type` is opens the chart of accounts.
Nothing on the payroll screen says that is where to go.

`one_hr/payroll.ready()` sets the type on every company's nominated account that
has none. It is not a decision: erpnext named the account and nominated it, and
this is the missing half of a sentence erpnext started.

### Salary Slip

Found:

1. **The list did not say what anybody is paid** — Employee Name, Status,
   Employee, Posting Date, Salary Structure, ID, and no money. It also named the
   person twice, because the `employee` link column now renders the title.
2. **The record does not either, on the tab it opens on.** The money is on the
   third and fourth tabs; Details carries Department, Letter Head, Designation,
   Payroll Frequency, Salary Structure and two dates.
3. `Status` repeating the header's own Draft pill, and `Currency` beside amounts
   already formatted in it.

Done: `net_pay` joins the list and `employee` leaves it; the headline reads
*6,000.00 د.إ for 01-08-2026 – 31-08-2026, a whole month*, and when it was not a
whole month it says how many of the working days were paid; Status and Currency
hidden.

**The names sweep grew a second half.** Turning `show_title_field_in_link` on
made the `employee` column read the person's name, so a list whose title is
already the name said it twice — *Rania Sabbagh · Draft · Rania Sabbagh*.
`names.py` now also takes `employee` out of the list view, on the 29 doctypes
where `employee_name` is the title field and the link is a column. Everywhere
else the link column stays, because it is the only place the person appears.

Left for the Tax & Benefits walk: **Deduct Tax For Unsubmitted Tax Exemption
Proof**, alone in an unlabelled section on every payslip, is one of a family of
India-specific payroll fields that wants one decision rather than six.

### Payroll Entry

The list said `ID · Status · Currency · Branch` — an empty branch column, three
letters of currency, and nothing about the run: not the period, not how many
people, not how much. The record was no better: the Overview tab carries the
posting date, the currency, the exchange rate, the payable account and two
checkboxes, and `number_of_employees` is a read-only field parked in the
employee filter section rather than on it.

Done: `start_date`, `end_date` and `number_of_employees` join the list and
branch and currency leave it. The headline reads *01-08-2026 – 31-08-2026: 5
people, 27,500.00 د.إ, in 5 slips still in draft*, and turns green when they are
all submitted. The total is counted off the slips rather than the `employees`
table, because the table is who was *selected* and the slips are what was
actually worked out. Currency, Exchange Rate and Status hidden — the last
because the header already carries the pill.

### Nobody is asked what currency they are paid in

Twenty-two HR and payroll doctypes carry a `Currency` link, and on a
single-company site every one shows the same three letters beside an amount
already formatted in them. `one_hr/money.py` hides the fourteen that are
`read_only` or have a `fetch_from` — filled by the framework or by their own
controller, so hiding one cannot stop a document being saved. That is the whole
test, and it is checked against the schema rather than assumed.

What stays visible, and why: **Salary Structure** declares the currency that
assignments and slips fetch from, so it is the one place the answer is given;
**Job Applicant**, **Job Opening** and **Job Opening Template** quote a salary
range on an advertisement, which a workspace may genuinely want in somebody
else's currency; the two **Employee Tax Exemption** doctypes belong to the
India-specific surface, which gets one decision rather than six; and **Payroll
Entry** is hidden by its own customization instead, because it is neither
read-only nor fetched — their form script fills it from the company, which was
checked in the browser rather than read off the schema.

OneBook is deliberately untouched. A single company can still be owed money in
somebody else's currency.

### Salary Structure Assignment, Additional Salary

Thin. Neither list carried the one number it exists to hold: the assignment
list read Employee Name, Status, Salary Structure, ID with no **Base**, and the
additional salary list no **Amount**. Both added, with the date beside them.

A seeding artifact worth writing down because it looked like a defect: every
assignment read an Annual Gross Earning of 36,000 whatever the base. HRMS
computes it with `frappe.get_cached_doc("Salary Structure", ...)`, and the
structure had been edited with `frappe.db.set_value` on a child row, which does
not clear that cache. The numbers were recomputed and are right. Nothing to fix
upstream — but it is a good reason never to edit a structure by its rows.

### Salary Register

It opened on **Nothing to show** with five submitted slips in the table. The
report ships `from_date` at today minus a month and `to_date` at today, and its
query keeps a slip only when the whole slip sits inside the range — so a
month-ago-to-today range can never contain a whole payroll month. Calendar
months do not fix it either, because payroll for August is read in September.

Done: the dates come from the newest submitted slip, so the register opens on
the run somebody most recently made. A default and not a rule — a person who
wants another range types one, and nothing resets it. Five rows where there were
none.

Its **Currency** filter is swept the way Company already was, and only on a
payroll or HR report, where the answer is always what the company pays in. And
a **Company** column is dropped from every report's columns, for the same reason
the filter is.

### Salary Withholding

Found: the **Reason** — why somebody's pay is being held, which is the whole
point of the record — sat behind a collapsed section; **Status** repeated the
header's own Withheld pill; and the list showed a **Relieving Date** that is
empty for everybody who has not left, and neither the period held nor the
cycles. Done: the reason section opens, Status hidden, and From Date and To
Date are the list instead.

### CTC Break-up — looked at and left

It opens on *Please set filters* with Employee and Salary Structure Assignment
outlined in red, and a `Filter missing` thrown in the console behind it. That is
frappe's own empty state and it says what to do.

**Defaulting the employee to the reader was considered and rejected.** A CTC
break-up is a pay-confidential figure and the rail entry sits in the Pay group,
which is the payroll officer's; defaulting it to *them* would be the wrong
person on every open. The version of this that is right is the `@me` sentinel on
an ESS screen, which already exists, rather than a default on a payroll one.

## Tax & Benefits

**A question for the product, not a fix.** Every screen in this group was empty,
and the company on this site is in the **United Arab Emirates**, where there is
no personal income tax. Six of the eight rows — the two exemption doctypes, the
two benefit doctypes, Professional Tax Deductions, and the income tax pair —
exist to model a tax regime a workspace either has or does not. A workspace that
does not have one is looking at six screens it can never use.

The shape of an answer already exists in this app: `one/company.py` derives from
what the site *is* rather than from a fixture, and hrms's own income tax
machinery is driven by whether an **Income Tax Slab** exists. "No slab, no
income tax here" is a derived condition, not a new setting, and the screens
would come back the moment somebody wrote one. Benefits are the same shape
against a salary component marked as a flexible benefit.

**Not done here.** Hiding six rail rows is a decision about what the product is,
not about what a screen says, and it wants a yes rather than an assumption. What
follows is the audit of the screens as they stand.

### The payroll year

The same gap as the leave year, in the other half of the framework. Nothing in
HRMS creates a **Payroll Period**, and `Salary Slip.payroll_period` asks
`get_payroll_period(start, end, company)` for one the moment a workspace has an
Income Tax Slab — without it there is no period to spread a year's tax across,
and two of the four reports in this group make it a required filter with no
default. `set_the_working_day` now creates the calendar year beside the leave
period. Its autoname is `Prompt` rather than a series, so unlike the leave
period this one is named at birth rather than renamed after.

### Exemption Declaration, Exemption Proof

Both open on a Details tab carrying the employee, the payroll period, the
department and the currency, and put the table and the two totals on a second
tab — the Salary Slip fault again. And both totals matter rather than one: a
category carries a `max_amount`, so somebody can claim thirty and be allowed
twenty, and nothing said which had happened.

Done: one headline for both, out of `public/js/exemption.js` — *Rania Sabbagh
claimed د.إ 36,000.00 for 2026, and all of it is allowed*, and in orange when
part of it is over a category limit. Both totals join both lists. The Currency
field is hidden on both: these are the two the money sweep deliberately left
because they are neither read-only nor fetched, and the reason is that their own
form script fills the field from `get_employee_currency`, which is in a `.js`
file the schema rule cannot see. They are named in `money.ALSO` rather than
found.

### The four reports

All four now open on something. **Income Tax Computation** and **Accrued
Earnings** required a payroll period and defaulted it to nothing, so both opened
on a red box; they now open on the period containing today. **Income Tax
Deductions** and **Professional Tax Deductions** take a month and a year and
default the month to whatever month it is today — the Salary Register fault in
another shape, because payroll for August is read in September; they now open on
the month of the last payroll run.

All four still show nothing, and that is the honest answer: this workspace's
salary structure has no deduction components, so no tax was deducted from
anybody. `Income Tax Deductions` is written for this — it asks
`erpnext.get_region(company) == "India"` and drops its Indian columns elsewhere.

### Benefit Application, Benefit Claim

The worst of the group, and all of one kind: **a read-only field that only the
form script fills.**

`max_benefits` on the application and `max_amount_eligible` on the claim are
both written by a whitelisted method their own `.js` calls, and both are then
compared against in `validate`. A document made any other way has `None` there,
and validate does not say so — it reaches

    if rounded(total_benefit_amount, 2) > self.max_benefits:

and raises **`TypeError: '>' not supported between instances of 'float' and
'NoneType'`**, naming neither the field nor what is missing. It is the same
fault as `leave_balance` on a Leave Application, and it gets the same answer:
`one_hr/benefit.py` calls the method upstream already wrote, before validate,
when the field is empty. With that in place the same insert answers *"Benefit
amount of component Medical Allowance should be greater than 0"* — a sentence
somebody can act on.

Worse, and visible on the screen rather than only in an API: **`total_amount`
and `remaining_benefit` are computed in eleven lines of their form script and
nowhere on the server.** A submitted application read *Total Amount 0.00* and
*Remaining Benefits 0.00* above a table holding one row of 9,000 against a
maximum of 12,000 — three numbers on one screen and two of them wrong. Adding up
a table is not a decision, so it is done in `before_validate`. A second
application, made the same way, reads 12,000 / 7,500 / 4,500.

Both totals join the application's list, which said only who and which period.

**The claim could not be exercised end to end, and that is honest rather than
broken.** `max_amount_eligible` comes from the benefit *ledger*, which salary
slips write as the benefit accrues; with no slip carrying the component nothing
has accrued, so nothing is claimable and the form says so. Building that fixture
means a payroll run carrying a flexible benefit, which is a long way to go for a
subsystem this workspace may not want at all — see the note at the top of this
group.

## Expenses

### Expense Claim

**The fourth request doctype, and the fourth approval shape.** HRMS gives this
one an `approval_status` Select — Draft, Approved, Rejected — that the approver
edits by hand, and then `on_submit` throws *"Approval Status must be 'Approved'
or 'Rejected'"* if they forgot, which is a rule the toolbar's own Submit button
does not carry. Attendance Request had no way to say no at all, Shift Request
had a dropdown, Leave Application had a dropdown and a throw. This is the last
of the four, and it now has the same two buttons, the same note dialog and the
same three signed fields, out of `one_hr/decision.py`.

The headline says what approving pays: *Approving this pays Omar Haddad back
د.إ 420.00.* It counts the rows only when there is more than one, names an
advance when one covers part of it, and says both numbers when the sanctioned
amount differs from the claimed. HRMS's own `validate_for_self_approval` still
runs and still refuses: nobody approves their own claim, whatever they press.

Measured: `HR-EXP-2026-00001` went to Approved, signed by the approver with the
note, and HRMS's own status moved to Unpaid.

Also found:

1. **`cost_center` is required on every expense row to book the claim**, and it
   is filled by their form script — from the claim, which is filled from the
   company. A claim made any other way fails on submit with *"Row 1: Cost Center
   is required in the expenses table"*. It is a better message than most in this
   audit and still a field nobody typed, because a workspace has one cost
   centre. `before_validate` fills the claim's from the company and each row's
   from the claim.
2. **Three money columns in the list**, two of them the same number and one that
   stays at nought until the status beside it says Paid. Grand Total stays,
   Total Claimed Amount and Total Amount Reimbursed go, and Posting Date — which
   had a filter and no column — joins them.
3. **`From Employee`** is the person every other screen in OneHR calls the
   employee. Relabelled.

Left: the Totals block still stacks six fields — sanctioned, advance, grand
total, claimed, taxes, reimbursed — and on a single-row claim four of them are
the same number and two are nought. They are not redundant in general (an
advance and a tax make them differ), so the headline answers the question
instead of the layout being rewritten.

### The accounts erpnext nominates, again

The payroll payable account was the first of these and the employee advance
account is the second, so the fix moved out of `one_hr/payroll.py` into
`one_hr/accounts.py`, which holds the table.

erpnext's standard chart of accounts creates **Employee Advances** under Loans
and Advances with

    {"account_type": "Payable", "account_category": "Other Receivables"}

— it contradicts itself in adjacent lines, on an account whose root type is
Asset — and names `Company.default_employee_advance_account` after it. An
advance is money the employee owes back, so Receivable is right, and
`Employee Advance.validate` says so: *"Employee advance account Employee
Advances - ONE should be of type Receivable."* No advance can be made on a
fresh site, for the same reason no payroll run could.

Corrected only where the value is still exactly what erpnext shipped — an unset
type for the payroll account, `Payable` for the advance one — so a workspace
that chose its own keeps it.

### Employee Advance

Thin once the account was right. Every field carries a description, which is
more than most screens in this audit manage, and one of them is wrong: **Advance
Amount** was described as *"Amount of expense"*, which is a different field on
the same form. It now says what it is — what the company hands over up front,
before anything is spent or claimed.

### Travel Request, Purpose of Travel

**Who is travelling, and why, were both behind collapsed sections** — Employee
Details and Description — while Travel Funding, Details of Sponsor and Copy of
Invitation were in the open. That is a form for sponsored conference travel
rather than for a business trip, which is what the rail row is for. Both
sections now open.

**Left, and worth naming:** a Travel Request has no status and no approver. It
is submitted, and that is the whole of it — so unlike the other four requests in
OneHR there is nothing to approve and nothing to sign. Giving it the two buttons
would mean inventing a workflow HRMS deliberately does not have, which is a
product decision rather than a screen fix.

`Purpose of Travel` is a two-field list of names, and there is nothing to say
about it beyond that it was empty; three were seeded to make Travel Request
usable.

### Vehicle Log

A vehicle log exists to answer how far and on how much, and it said neither.
The record carried **Last Odometer 49,110** and **Current Odometer 49,880** and
not the 770 between them; the litres and the price — the whole subject of a
refuelling record — were behind a collapsed **Refuelling Details** section; and
the list was `ID · Status · License Plate · Employee`, with no date, no odometer
and no fuel.

Done: the section opens, the date, the odometer and the fuel join the list, and
the headline reads *770 on the odometer since the last log, on 58.00 Litre
costing د.إ 179.80 — 13.3 per Litre*. The unit is asked of the vehicle rather
than assumed, because `Vehicle.uom` is what the fuel is measured in.

### Unpaid Expense Claim, Vehicle Expenses

Unpaid Expense Claim works and answers one row — the claim approved earlier in
this walk, which is unpaid, which is the whole question.

**Vehicle Expenses opened on a red modal**: *Start Year and End Year are
mandatory*, thrown before the page had drawn. Its `fiscal_year` filter defaults
to `frappe.defaults.get_user_default("fiscal_year")`, and nothing on the site
ever sets that — erpnext creates the Fiscal Year and never nominates one.

Two things, because one of them alone leaves the modal. `accounts.year()` points
the site's default at the fiscal year containing today, re-pointed on every
migrate rather than written once, because a default that is right in January and
wrong the following January is worse than none — that is what removes the modal,
because the filter resolves before the first run. And `reports.js` now fills an
empty **Fiscal Year** filter the same way it already filled **Payroll Period**,
which covers the moment between two years. The report answers two rows and
368.90 د.إ.

## Hiring

Nothing existed here, so the chain was seeded first: three Interview Types with
their skill sets, a Job Requisition, a Job Opening, two Job Applicants, an
Interview and a Job Offer. Four things refused on the way and each was hrms
asking for a record that has to exist first — a `Skill` before an expected skill
set, an `Offer Term` before an offer term, a Job Requisition status that is
`Pending` rather than `Open`, and an `interview_type_name` that is not marked
required and is what the record is named after. Worth one line each in the audit
and none of them a screen.

### Job Applicant, Interview

**A Job Applicant is named after their email address.** `autoname` in the
doctype says `HR-APP-.YYYY.-.#####` and `JobApplicant.autoname` overrules it
with `self.name = self.email_id`, so every applicant's id is
`nadia.khoury@example.com`. That is fine for the applicant's own screen, where
the title field carries the name, and it is not fine anywhere that links to one:
the **Interview list read `nadia.kho…`** as its first column, because `Interview`
has no name of its own and takes the applicant's docname as its title.

Done: Job Applicant gets `show_title_field_in_link`, so every link to one reads
the person's name. Interview gets a hidden `one_applicant` fetched from
`job_applicant.applicant_name` and takes it as the title field, so the list
reads **Nadia Khoury**. The `job_applicant` column then said the same thing
twice and came off, which is the `names.py` rule applied by hand to a link that
is not `employee`. `to_time` came off as well: a scheduled interview is a date
and a start, and its end is on the record.

Job Applicant itself is in good shape. HRMS ships the verbs — **Shortlist**,
**Reject**, **Schedule Interview** — on the toolbar, and the status they set is
the same dropdown beside the header pill. It is deliberately left editable,
unlike the four request doctypes: the buttons only cover Open to Shortlisted or
Rejected, and Hold, Replied and Accepted would become unreachable.

### Job Opening, Job Offer, Staffing Plan

Three list faults and one duplicate.

**Job Opening** put its **Description** in the list — a paragraph of prose in a
column, squeezing the job title beside it down to *"Site Engine…"*. It comes
off; the description is on the record, which is where a paragraph belongs.

**Job Offer** named the applicant three times: the Job Applicant link, Applicant
Name and Applicant Email Address. With `show_title_field_in_link` now on Job
Applicant the link reads *Nadia Khoury*, so `applicant_name` is a mirror and is
hidden. The email stays, because it is a second fact rather than the same one.

**Staffing Plan's list was `ID · Status` and nothing else** — not the period it
covers, not the headcount, not the money. From Date, To Date and Total Estimated
Budget join it.

Job Requisition and Employee Referral needed nothing: both lists already carry
what the screen is about.

### Appointment Letter

**The fourth instance of the same fault**, after `leave_balance`, the two
benefit ceilings and the expense claim's cost centre. `introduction` and `terms`
are both required on an Appointment Letter and both are filled by eleven lines
of their form script when somebody picks a template. Nothing on the server does
it, so a letter made any other way — an import, an API, the onboarding
automation a workspace writes for itself — is refused with `MandatoryError:
[Appointment Letter, HR-APP-LETTER-00001]: terms`, naming a table it cannot see
how to fill.

`one_hr/letter.py` reads the template before validate when the fields are empty.
Their helper answers `[{introduction, closing_notes}, {"description": [rows]}]`
— the terms arrive under a key called `description`, which is also the name of a
field on each row — so it is read exactly the way their own form script reads
it. A letter that already carries terms keeps them, because somebody edited them
deliberately.
