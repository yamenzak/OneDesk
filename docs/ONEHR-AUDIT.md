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

**Open, not yet fixed:** approving prints *"Please set default template for
Leave Status Notification in HR Settings."* on every approval. HRMS ships
`send_leave_notification` on and no template to send, so the product promises an
email it cannot deliver and nags instead. The fix is to ship the two Email
Templates — Leave Approval and Leave Status — as fixtures, not to switch the
setting off.
