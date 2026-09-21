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
Lifecycle" — but the dashboard view draws its heading elsewhere. **Still open.**

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
