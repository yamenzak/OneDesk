# OneHR

Written by hand. What OneHR does and how to use it, screen by screen. Everything
above **Under the hood** is written for the people who use OneHR, and OneAI
reads it to answer "how do I…" questions. Under the hood is for the people who
build it.

OneHR is HR for one company: people, attendance, leave, pay, expenses, hiring,
appraisals, and joining and leaving. It is built on Frappe HRMS, so every
record HRMS has is here, and OneHR fixes what HRMS leaves unfinished and adds
what it lacks.

## Finding your way

The rail on the left has the whole of OneHR in it:

- **Home** — the page everybody starts their day on. **Check In**, **Request
  Leave** and **Claim an Expense** are its buttons, and the leave you have left
  is at the top. **Today** lists your own requests still waiting, the ones
  waiting for you to answer, and, for HR, check-ins flagged, passports, visas
  and permits running out, contracts and probations ending, and today's
  interviews. HR also sees the headcount, who joined, who is in and away today,
  the last payroll and the open positions, and an **Overview** of the people,
  their time, their pay and hiring. **Everything**, **Reports** and **Setup**
  list the whole of OneHR with what each is for.
- **Overview** — who is in, who is absent, who is on leave, and flagged
  check-ins waiting for a look.
- **Employee**, **Org Chart**, **Setup**.
- **Time**, **Leave**, **Pay**, **Tax & Benefits**, **Expenses**, **Hiring**,
  **Growth**, **Joining & Leaving** — one group each, opened with the arrow.
  Pay has Employee Incentive, Retention Bonus, Arrear (back pay for a raise
  dated in the past) and Payroll Correction (days without pay given back);
  Growth has Transfer; Joining & Leaving has Exit Interview and the Full and
  Final Statement.

**One workspace is one company.** You are never asked which company a record
belongs to, and no screen, filter or report shows a Company field. Pay is in
the company's currency, so no payroll screen asks for a currency either.

**Names, not IDs.** Everywhere a record points at an employee, applicant,
leave policy or leave year, it shows the name — *Rania Sabbagh*, *Standard*,
*2026* — rather than `HR-EMP-00001`.

**OneAI is the round button in the corner.** Open it on any page and it offers
what makes sense there — "Claim a receipt" on expense claims, "Check this
payroll" on a payroll entry. No OneAI button is ever put on a page itself. See
**OneAI in OneHR** below.

## The employee record

An employee's record answers the questions people open it for before anybody
clicks anything: where they are today, how much leave they have left, what is
waiting on an approver, what they are paid under, and how long they have been
here — and, when they hold any, how much of the company's equipment they
have. Each answer links to the record it came from.

**Identity Documents** — passport, national ID, residence permit, work permit,
visa, driving licence — each with its number, issue and expiry dates and a
scan.

**Attendance Standing** is a score out of 100, worked out every night from the
last 90 days of check-ins. It never refuses anybody; it decides whose check-ins
count when OneHR learns a new office network or location.

**When somebody leaves**, setting their **Relieving Date** does everything that
should follow: on that day their status becomes Left, their login is switched
off, their passkey stops working, and their shift assignments end. A date set
in advance takes effect on the day. **Notice Ends On** shows the resignation
date plus the notice period.

Their **Separation** is the leaving checklist. HR submits it, and each step
becomes a task for its person: an exit interview, the final pay, and, for each
piece of the company's equipment they hold, a Return step for the stores.
Joining works the same way with an **Onboarding**.

## Clocking in

Employees clock in and out themselves from any phone or computer. There is no
machine to buy.

**Check In, in the bar at the top.** It sits at the bar's right end, with
OneIntake, Timers and Notifications, and has a dot: green while you are
clocked in, grey while you are not. On a phone it is at the top of the panel. Click it to clock in or out. It picks the right direction itself, and it does not
appear for somebody on leave or on a holiday, for anybody without an employee
record, or when the workspace has not turned self check-in on.

**Before the first clock-in, register a passkey on your phone.** It is a key
your phone keeps and unlocks with your face, fingerprint or PIN. Registering
has to be done on a phone, not a desktop computer, and that holds for every
employee whether or not the clock is on: one made on the office computer would
check them in the day the clock is turned on. At the office computer, *Sign in with a Passkey* shows a code to
scan with that phone, and the password still works. Each employee has one
passkey; after that it works on your other devices too, because iCloud and
Google sync it. Every clock-in asks for your face or PIN again. Clocking in
from your laptop with the synced passkey is not flagged for that; a passkey
that stays on one phone turning up in another browser is (`passkey-elsewhere`).

**A lost or new phone.** The screen that refuses you has a button to ask HR
for a reset. HR sees what your new phone looks like next to your old one, and
resets it in one click.

**Signing in with your passkey.** The same passkey signs you in: the login
page leads with *Sign in with a Passkey*, and no password is needed. A passkey
belongs to the login rather than the employee (`Clock Device.user`), so
anybody can have one; an employee's is also the one the clock reads, which is
why only HR resets it.

**What a clock-in checks**, in this order:

1. **The passkey** — that it is you.
2. **The network** — that you are on one of the workspace's known networks.
3. **The location** — that your phone says you are inside one of the places
   you work. Your browser asks for permission to share your position.
4. **A photo** — only if the workspace turns it on. It is taken in the page;
   no file is uploaded.

The network and the location prove the same thing two ways, so by default
either one is enough. A workspace can ask for both.

**If a clock-in is refused**, the screen says why in plain words: which of the
checks failed. Every attempt, allowed or refused, is written down as a
**Clock Attempt** with a score out of 100.

**Working from home or somewhere else.** Ask for it first with an
**Attendance Request**. Once it is approved, being off the network and away
from every location costs you nothing on those days. A home network can also
be learned for one person, so home counts like the office.

**Clocking out** asks for a reason — Break, Lunch, Errand or Done for the day
— when the workspace turns that on. You can clock in and out several times a
day. If you forget to clock out, the day is closed at the end of your shift,
you get one reminder, and the log says it was closed automatically.

**OneHR fixes its own settings.** When the office router gets a new address,
or everybody clocks in at a gate outside the drawn location, check-ins from
people who were verified another way are noticed. After enough of them — the
**Confirmation Threshold**, three by default — the new network or location is
added, and HR Managers are told and can reject it. This only ever widens
*where* people may clock in, never *who* may.

**The review queue.** **Clock Attempt** opens on the check-ins that were
flagged and nobody has looked at yet. Each shows everything the check-in saw.
Accept or reject it; a rejected one does not count towards attendance.

**Places and networks.** **Clock Place** holds the circles people may clock in
from, with a radius. **Clock Network** holds the office addresses, one address
or a range. Rows marked Proposed were learned by OneHR: open one and press
**Confirm** or **Reject**. A rejected one is never proposed again.

### Attendance settings

The rail's **Attendance Settings** opens HR Settings on its Attendance tab:

- **Allow Employees to Check In Themselves** — the main switch, off until a
  workspace turns it on.
- **Auto Close Open Check-ins at Shift End**, **Ask for a Reason on Check
  Out**.
- **Require a Passkey**, **Refuse Check-in Without a Passkey**, **Check the
  Network**, **Check the Location**, and **Network and Location**: Either or
  Both.
- **Refuse Below Score** (50) and **Flag Below Score** (85).
- **Ask for a Photo**, **Delete Photos After (Days)**.
- **Learn New Networks**, **Learn New Locations**, **Include Personal Networks
  and Locations**, **Confirmation Threshold**.
- **Standard Working Hours (Per Day)** and **Allow Geolocation Tracking**,
  which the location check needs.

### Before attendance works

The setup wizard asks when people work — start, end and the weekly day off.
From that it makes this year's holiday list (with the country's public
holidays), assigns it, creates a **Day** shift ready to turn check-ins into
attendance, and creates the leave year and the payroll year.

If a shift is not set up to turn check-ins into attendance, its form says so
and offers **Read Check-ins**, and HR Managers are told once a week about any
shift that has check-ins and is producing no attendance.

### Marking attendance by hand

For people without a phone, or a day the clock did not cover: **Mark
Attendance** in the rail. Pick the day, then who, then what to mark them as.
**Tick Everyone Who Checked In** ticks everybody who clocked in that day, and
**Search** narrows a long list without losing the ticks.

### Requests and their answers

**Attendance Request** asks for days to count as worked — Work From Home, On
Duty, Customer Site, Training, Missed the Clock, or a reason the workspace
adds. **Shift Request** asks to work a different shift.

Both are answered the same way as leave and expense claims: **Approve** or
**Reject**, with a note. The record then shows who decided, when, and what they
wrote. Nobody approves their own request.

### Overtime

Record overtime from the employee's record or from the day's attendance: the
dialog shows the day and the standard working day before it writes anything.
An **Overtime Slip** collects the month's overtime into an Additional Salary
for payroll. A day's overtime cannot be paid twice.

### Timesheets

The timer on a timesheet only resumes a row that has a start and no end, and
it uses one clock, so a typed block keeps the hours that were typed.

### Time reports

- **Attendance Overview** — today's numbers and the month.
- **Monthly Attendance** — one row per person for the month, including
  everybody with nothing marked, with holidays filled in.
- **Attendance by Shift** — every day in the period, including days with no
  shift, which it counts separately.
- **Hours Utilization** — hours logged on timesheets against the working days
  each person actually had. Drafts are counted separately.
- **Employee Checkin** — each log says whether it was Counted, Rejected,
  Flagged or Not counted yet.

### Who can do what with attendance

- **Employees** clock in and out, and see their own passkey and attempts.
- **HR Users** reset passkeys, work the review queue, mark attendance by hand
  and answer requests.
- **HR Managers** set the rules, block a passkey, and confirm or reject a
  learned network or location.
- Nobody approves their own team's devices.

## Leave

**Leave Application.** The approver presses **Approve** or **Reject** and can
add a note. The page says what approving does: *Approving this books 3 days of
Annual Leave for Rania Sabbagh, 01-10-2026 to 03-10-2026, leaving them 18.* The
employee is emailed the answer, with the note.

**The leave year** is created by the setup wizard, named after its year.
**Leave Control Panel** opens ready to allocate: the leave year's dates filled
in and the leave policy chosen when there is only one.

**Leave Allocation** lists how many days each allocation gives.
**Leave Policy Assignment** shows policies by name and when each starts.

**Leave Encashment** says the amount before you submit — *Submitting this pays
Lina Farah AED 700.00 for 7 days of Casual Leave* — or says what is missing:
the daily encashment amount on the salary structure or the person's
assignment. OneHR does not guess a daily rate.

**Reports:** **Leave Balance**, **Leave Balance Summary** and **Working on a
Holiday**. An employee can have a holiday list of their own that differs from
the company's; Working on a Holiday reads theirs.

## Pay

**Payroll Entry** says the whole run in one line: *01-08-2026 – 31-08-2026: 5
people, 27,500.00, in 5 slips still in draft*, and turns green when they are
all submitted. The payroll payable account is set up correctly out of the box,
so the first run works.

**Salary Slip** shows the net pay in the list, and the slip says the amount and
the period, and how many working days were paid when it was not a whole month.

**Salary Register** opens on the most recent payroll run.

**Salary Structure Assignment** and **Additional Salary** show the amount in
the list. **Salary Withholding** shows the reason, and the period held.

**CTC Break-up** needs an employee and an assignment chosen before it shows
anything.

## Tax & Benefits

These screens are for countries with personal income tax or flexible
benefits. In a country without income tax, like the United Arab Emirates, they
stay empty.

**Exemption Declaration** and **Exemption Proof** say how much was claimed and
how much is allowed, in orange when part of a claim is over a category's limit.
**Benefit Application** and **Benefit Claim** work out their own limits and
totals. The four tax reports open on the current payroll year or the month of
the last payroll run.

## Expenses

**Expense Claim.** The approver presses **Approve** or **Reject** with a note,
and the claim says what approving pays: *Approving this pays Omar Haddad back
AED 420.00*, including any advance that covers part of it. Nobody approves
their own claim. The cost centre is filled in.

**Employee Advance** works out of the box: the advance account is set up
correctly.

**Travel Request** shows who is travelling and why at the top. It has no
approval step.

**Vehicle Log** says the distance and the fuel: *770 on the odometer since the
last log, on 58.00 Litre costing AED 179.80*.

**Who handles them.** An **HR User** makes and submits advances, travel
requests and vehicle logs, and an **HR Manager** also cancels them and keeps
the list of purposes of travel. HRMS gives these to roles nobody is given in
One (System Manager, Expense Approver, Fleet Manager), so One gives them to
HR (`access.py`). What an employee sees of their own is unchanged.

**Reports:** **Unpaid Expense Claim** and **Vehicle Expenses**, which opens on
this year.

## Hiring

OneAI works through the whole of hiring, and a person makes every decision.
Nothing OneAI does changes an applicant's status or contacts the candidate.

**Job Opening.** Write **Screening Criteria** — what a strong applicant has, one
per line. Every applicant is rated against them. OneAI's panel on the opening
offers **Write this opening**, which drafts the description and the criteria as
a change to approve. On a Job Requisition it offers **Draft the opening**.

**Job Applicant.** Each new applicant is read by OneAI in the background:

- **OneAI Rating** — stars, for how well the CV meets the Screening Criteria on
  its own.
- **Standing** — out of 100, against everybody else applying to the same
  opening. It moves as others arrive, and the applicant list is sorted by it.
- **OneAI Summary**, and a comment from OneAI with what the CV shows, what it
  does not, and what is worth confirming before you call.

The **Applicant Rating** beside them is yours and OneAI never touches it.
OneAI is told never to judge age, sex, gender, family status, religion, race,
nationality, disability, appearance, a photograph or what a name implies.
Anybody whose standing moves by 15 or more gets a comment saying why.

In the panel on an applicant: **Screen again**, **What should I ask first?**
and **Write a kind decline**. On an opening: **Rank the applicants again**.

**Interviewers.** Everybody named on an interview can open it and give
feedback on it, whatever else they use One for.

**Interview.** When an interview is made, OneAI writes **Interview
Preparation** onto it: what to confirm first, then up to eight questions, each
saying which skill it tests and why.

**Recording an interview.** Press **Record** on the interview. You must first
confirm the candidate has agreed; the recording keeps who confirmed it and
when. For a video call, tick **Include Audio From Another Tab** and pick the
call's tab. A bar at the bottom of the screen shows the time, a level meter,
and **Stop**; it says *No sound. Check the microphone.* after eight seconds of
silence. The recording keeps going if you move to another page, and the
browser warns you before you close the tab.

The recording is saved in five-minute parts as it goes, so a crash loses at
most five minutes. When it stops, OneAI writes the transcript, with
Interviewer and Candidate and a time on each turn, and comments on the
interview: what was said about each skill and when, what was not covered, what
to weigh and what to ask next round. The applicant gets a one-line summary.

The audio is deleted after a year by default (**Delete Recording Audio After
(Days)**) and the transcript stays. Until then only an HR Manager can delete
it. **Transcribe again** in the panel on a recording retries parts that failed.

**Interview Feedback.** In the panel on an interview, **Draft my feedback from
the recording** drafts your feedback with a rating for each expected skill,
for you to approve and submit. Only the interview's own interviewers can use
it.

**Job Offer** — **Write the offer terms** in the panel. **Appointment Letter**
fills in from its template. **Staffing Plan** lists its period, headcount and
budget.

**Hiring Pipeline** is the hiring report: one row per applicant, starting from
the opening, so an opening nobody applied to shows *nobody yet*. The tiles are
Openings, Vacancies, Applicants, Waiting, Interviewed, Offered and Accepted.

## Growth

**Goal.** In the panel on the goal list, **Draft my goals for this cycle**
drafts up to five goals from your role, last cycle's goals and your feedback,
each as its own card to approve. Managers can do it for their direct reports.

**Appraisal Cycle** moves to In Progress when its first appraisal is made. Each
appraisal takes the cycle's dates.

**Appraisal** says the person, the period, the score, and which of the three
scores — goals, feedback, self appraisal — is still missing. In the panel:
**Draft my feedback** and **What training would help?**, which matches the
weakest areas to the workspace's own training programs and events.

**Employee Promotion** says the change in one line — *Omar Haddad, from
01-07-2026: designation Engineer → Senior Engineer* — and the list shows the new
designation, so it can be filtered.

## Joining & Leaving

**Onboarding** needs a Job Offer, and the first one a workspace submits goes
through: the holiday list and the project dates are taken care of.
**Separation** shows its status in the list. Submitting one adds a **Return**
task for each asset the person holds (a laptop, a phone), for whoever looks
after the company's equipment; see OneInventory.

**End of Service** is HRMS's Gratuity. It works out what a leaver is owed by a
rule (in the UAE, days of basic pay for each year served) from their last
payslip, and the books pay it. HRMS's UAE rules count no pay at all until a
pay component is added to them. The demo adds Basic Salary.

**Grievance.** Each new grievance is read by OneAI: a neutral summary, a
category and an urgency. One about harassment, discrimination or safety is
marked **Sensitive**, and from then on only HR Managers and the person who
raised it can see it, anywhere. HR Managers are told at once about a sensitive
or urgent one. OneAI never takes the mark off; only an HR Manager can.

**Letters.** An employee asks for a salary certificate, an experience letter,
an employment letter or a no objection certificate in the OneAI panel (**Ask HR
for a letter**). OneAI drafts it from their own record, the employee approves
the draft, and HR Managers are told. HR reads it and issues it by submitting.
It prints on the letterhead, marked *Draft. Not issued.* until then. HR can
ask for a letter about anybody from the employee's record.

**Training Program**, **Training Event**, **Training Feedback** and **Training
Result** list what each is about and when.

**Exits.** **Employee Exits** opens on this year, so it shows who has left and
who is leaving. In the panel on exit interviews, **Why are people leaving?**
counts the reasons given over the last twelve months.

**Reports:** **Lifecycle Overview**, **Employee Birthday**, **Employee
Information** and **Employee Analytics**, which opens on Department.

## OneAI in OneHR

Open the OneAI panel on any page. It offers what fits that page; you can also
just ask. Anything OneAI would write is shown as a card, and nothing happens
until you approve it — except the background work listed after this table,
which only writes OneAI's own fields and comments.

| On | Offered | What it does |
|---|---|---|
| Home | Book time off, Claim a receipt, How much leave do I have?, Ask HR for a letter | |
| Leave | What is our leave policy? | Answers from the leave types, holidays and notes, naming each source |
| Expense claims | Claim a receipt, What can I claim? | A claim from a photo of a receipt |
| Payroll entry | Check this payroll | Every slip against last month, and anybody missing |
| Salary slip | What changed since last month? | The same for one slip |
| Employee (HR) | Write a letter for this person | |
| Goals | Draft my goals for this cycle | |
| Appraisal | Draft my feedback, What training would help? | |
| Exit interviews | Why are people leaving? | |
| Any settings page | Help me set this up | Goes through the settings and suggests changes |
| Hiring | see **Hiring** | |

**Asking about a policy.** "How many sick days do I get?" is answered only
from what this workspace has written down — its leave types, holiday list and
the notes an administrator added in AI Knowledge — and each part of the answer
names where it came from. When nothing covers the question, OneAI says so.

**Asking how OneHR works.** OneAI reads this page to answer questions like
"how do I register my passkey?" and names the section it used.

**What runs on its own**, each with a switch on OneIntake › Settings, under
OneHR, with the rest of what OneAI does by itself when something arrives:

| When | What | Switch |
|---|---|---|
| A new applicant | Rated and ranked | Screen New Applicants |
| A new interview | Questions prepared | Prepare Interviews |
| A recording ends | Transcribed and commented on | Transcribe Interview Recordings |
| A new grievance | Summarised and categorised | Triage Grievances |

Whether interviews may be recorded, and how long their audio is kept, are
HR's policy and stay in HR Settings.

Each is one AI call per event and uses the workspace's AI credits. Comments
from these are written by a user called **OneAI**. Which model each uses is set
on OneAI › Actions: **Screen Applicants**, **Interviews**,
**Grievances** and **Transcribe Interviews**. Transcribe Interviews needs a model that reads audio.

## Connections

- **From One**: The setup wizard makes this year's holiday list, a Day shift, the leave year and the payroll year.
- **From OneIntake**: A CV becomes a job applicant, and a receipt an employee sends in becomes their expense claim. A sick note becomes a leave application, and a passport or permit is added to the employee's Identity Documents.
- **From OneInventory**: The employee record shows how much of the company's equipment the person holds. HR submits a separation, and it adds a Return task for each asset they hold, given to the stores.
- **From OneTask**: Time from a task's timer goes on the person's timesheet for the week.
- **To OneBook**: Payroll runs, expense claims and advances post to the accounts. OneHR sets up the payroll and advance accounts so the first run works. The VAT Return counts the VAT on expense claims.
- **From OneProject**: New Expense Claim on a project's Money starts an expense claim on that project.
- **To OneProject**: A day of attendance at a project's site is logged as time on the project. An expense claim says its project at the top. Approved expense claims for a project count as its costs, and a Time and Materials project bills them to the customer.
- **To OneCalendar**: Leave, interviews, holidays and who's off show as layers on the calendar. An employee's own calendar shows their leave.
- **To OneTask**: Each activity on an onboarding or separation checklist becomes a task for whoever does it.

## Under the hood

For the people who build OneHR. OneAI does not read past this heading.

### Where things are

| File | What it does |
|---|---|
| `employee.py`, `own.py`, `names.py`, `money.py`, `leaving.py` | The employee record's answers, who the reader is, names for IDs, currency, the last day |
| `heads.py` | Every OneHR Record Head (one/head.py): the employee's pill, quarter and numbers; the sentence each request and document opens on; Approve and Reject; a clock attempt's Accept and Reject |
| `clock.py`, `gates.py`, `rules.py`, `ledger.py`, `passkey.py`, `signin.py` | Clocking in, the four checks, the score, Clock Attempt, passkeys, passkey login |
| `presence.py`, `away.py`, `closing.py`, `healing.py`, `learned.py`, `review.py`, `checkin.py` | Who is in, approved days away, closing a day, learning networks and places, the review queue |
| `marking.py`, `overtime.py`, `timesheet.py`, `setup.py`, `shift.py`, `request.py`, `decision.py` | Marking by hand, overtime, the timer, shift readiness, requests and their Approve/Reject |
| `leave.py`, `encashment.py`, `payroll.py`, `accounts.py`, `benefit.py`, `expense.py` | Leave, encashment, payroll, the accounts erpnext nominates, benefits, expense claims |
| `growth.py`, `lifecycle.py`, `letter.py`, `policy.py` | Appraisals, onboarding, appointment letters, HR Settings defaults |
| `hiring.py`, `ai.py`, `ai_payroll.py`, `ai_letters.py`, `ai_policy.py`, `ai_grievance.py`, `ai_growth.py` | OneAI in OneHR |

Doctypes of our own: Clock Attempt, Clock Signal, Clock Device, Clock Network,
Clock Place, Clock Reason, Attendance Reason, Employee Document, Shift Location
Place, Interview Recording, Interview Recording Part, Employee Letter. Reports
of our own: Monthly Attendance, Attendance by Shift, Hours Utilization, Hiring
Pipeline; HRMS's versions of those four are disabled rather than deleted.

### Rules the code keeps

- **Never edit HRMS or erpnext.** Everything is a custom field, a property
  setter, a hook or a form script in this app. `docs/OVERRIDES.md` lists every
  upstream line we depend on.
- **A request is answered by Approve or Reject** from `decision.py`, the same
  on Attendance Request, Shift Request, Leave Application and Expense Claim:
  Status is read-only, and the record carries who, when and the note. The
  two buttons and the sentence above each record are its Record Head, in
  `heads.py`; no form script draws either.
- **A value HRMS's form script fills is filled on the server too**, before
  validate, when it is empty — `leave_balance`, the benefit limits, the expense
  cost centre, the appointment letter's terms, onboarding's holiday list. A
  record made by import, API or OneAI otherwise fails with an error naming a
  field nobody typed.
- **A report counts from the thing measured, not the records that exist.**
  Attendance by Shift, Monthly Attendance, Hours Utilization and Hiring
  Pipeline all left-join from the full set, so "nobody" is a row.
- **HR Settings defaults are written once**, by `policy.seed`, only where a
  field has never been written, because a Single reads an unwritten Check as 0.
- **OneAI's background work runs as the disabled user `oneai@one.invalid`**, so
  every comment has an author and nobody can sign in as it. A model answer that
  cannot be read goes to the error log with its text.
- **A `has_permission` hook returns True, never None.** frappe reads any falsy
  answer as a refusal.

### Upstream faults corrected here

Each is small, measured on a real site, and worth offering back to HRMS or
erpnext:

- Payroll Payable is nominated without `account_type`, and Employee Advances
  with the wrong one, so neither a payroll run nor an advance could be made.
- `Shift Type` silently produces no attendance without auto attendance, a
  process-after date and a last sync; `Holiday List Assignment` is required
  and nothing creates one.
- No Leave Period or Payroll Period is ever created, so the balance report and
  two tax reports opened on nothing.
- Every approval shows a stray "HR Telemetry Milestone already exists"
  message; `one/quiet.py` drops it.
- `validate_distance_from_shift_location` checks only the first of several
  shift locations.
- The timesheet timer resumes typed rows and mixes two clocks.
- An Overtime Slip's Fetch saves a record behind the form, and refuses anybody
  without a salary structure.
- An Appraisal never gets its dates, so its duplicate check across cycles never
  fires; an Appraisal Cycle never moves to In Progress.
- An onboarding project starts on the joining date, after its own first task.
- Recruitment Analytics only counts openings that have a staffing plan.
- Several reports open on defaults that can never match: Salary Register,
  Employee Exits, Vehicle Expenses, Employee Analytics.

### Deliberately not built

Face recognition, a native app, our own shift arithmetic, a Wi-Fi name check,
anything that trusts the phone's clock, random presence checks, a score nobody
can explain, reading a photo for its metadata. In hiring: automatic rejection,
anything that reaches the candidate without a person, reading tone or emotion
from a recording, video, a live transcript. Tax & Benefits screens stay in the
rail on countries without income tax; hiding them is a product decision not
yet made.

### Tests

`tests/test_hiring.py`, `tests/test_hr_ai.py`, `tests/test_hr_ai_more.py` and
the attendance, rules and wording guards. The e2e browser suite is not run on
a change.

### access.py

Who may do what in OneHR, where HRMS's defaults do not fit.

HRMS gives four of the Expenses group's kinds to roles nobody is given in
One: a **Travel Request** and its **Purpose of Travel** to the System Manager,
an **Employee Advance** to the employee and an Expense Approver, and a
**Vehicle Log** to a Fleet Manager. So the people officer the rail is for
could open none of them. An HR User now handles them, and an HR Manager runs
them. The purposes of travel are the HR Manager's list. HRMS lets nobody
submit a **Gratuity**, so HR Users and HR Managers are given that once, and a
change in Access afterwards stands.

The employee's own requests are unchanged: HRMS's Employee and Employee Self
Service rules still decide what they see of their own. A role that reads one
already, by HRMS's rules or the workspace's, keeps what it has (one/roles.py
`give`).

### accounts.py

The accounts erpnext nominates carry the type hrms demands of them.

Twice now the same shape has stopped a screen working on a site nobody had
touched: erpnext's standard chart of accounts creates an account, names the
company's default after it, and gives it a type hrms then refuses.

**Payroll Payable** is created under Accounts Payable with an `account_category`
and *no* `account_type`, and `default_payroll_payable_account` is set to it.
Payroll Entry answers *"Account type should be set Payable for payroll payable
account Payroll Payable - ONE, please set and try again"* and a payroll run
cannot be made at all.

**Employee Advances** is worse, because erpnext contradicts itself in adjacent
lines — `{"account_type": "Payable", "account_category": "Other Receivables"}` —
on an account whose root type is Asset. An advance is money the employee owes
back, so Receivable is right, and `Employee Advance.validate` says so: *"Employee
advance account Employee Advances - ONE should be of type Receivable."* No
advance can be made either.

Neither is a decision this product is making. erpnext named both accounts and
nominated both; this is the missing or mistaken half of a sentence erpnext
started, and it is corrected only where the value is still exactly what erpnext
shipped — a workspace that chose its own keeps it.

`year` in `accounts.py` is the third of the same kind: erpnext creates the Fiscal
Year and nothing ever makes it the site's default, so a report whose filter
reads `frappe.defaults.get_user_default("fiscal_year")` gets nothing.

`component` is the fourth: HRMS asks every earning for an account per company,
and erpnext's chart already has the Salary account it belongs in.

`year` points the site's default fiscal year at the one we are in. `Vehicle Expenses` defaults its `fiscal_year` filter to
`frappe.defaults.get_user_default("fiscal_year")` and then throws **Start
Year and End Year are mandatory** in a red modal, before the page has drawn,
on a site where nothing ever set that default. erpnext creates the Fiscal
Year; it just never nominates one.

It is re-pointed on every migrate rather than written once, because a default that
is right in January and wrong the following January is worse than none.

### ai.py

What OneAI can do in OneHR.

The tools and suggestions this module adds to the panel, named in `hooks.py`
under `one_ai_suggests` and `one_ai_suggestions`. The rules are OneAI's: a tool
runs as the person asking, and anything that would write is a card somebody
approves. What this module adds is what HR knows — whose employee record a
receipt belongs to, what a claim needs, which expense types this workspace has.

**A receipt becomes a claim, never a payment.** `claim_expense` reads nothing
the person could not, and writes nothing: it suggests an Expense Claim in their
own name with one row, and the receipt goes on the claim when it is approved.
The claim then goes through this workspace's approval like any other, which is
where a wrong amount is caught — by the person who approves expenses, not by the
model that read the paper.

`SUGGESTIONS` is what the panel offers, by doctype, when it opens on one. `file` means the
chip asks for a file first and then says `ask` with it. `can` is the verb the
reader must hold on the doctype for the chip to be offered at all. `view`
keeps it to the list or the form, and `expects` names the tool the question
exists to call — asked for once more if the answer came without it.

### ai_grievance.py

OneAI reading a new grievance: a summary, a category, and who may see it.

A grievance about harassment, discrimination or safety is the most sensitive
record a workspace holds, and HRMS lets every Employee read every grievance.
So a grievance OneAI reads as one of those is marked **sensitive**, and from
then on only HR Managers and the person who raised it can see it — in the
list, in a link, in a report and on its page. HR Managers are told at once.

**OneAI never clears the mark.** A model that misses a sensitive grievance is
a model that missed; a model that could also make one visible again would be
a model that exposed somebody. Only an HR Manager unticks it.

**Neutral, and nothing added.** The summary says what the person raised, not
who is right, and names nobody the grievance does not.

One call per grievance, run as OneAI in the background like the hiring work,
switched off in HR Settings.

### ai_growth.py

OneAI on growth: goals for a cycle, and the training that would help.

**Goals.** Writing three good goals is the part of an appraisal cycle people
put off, and the raw material is already here: the person's designation, the
KRAs this workspace appraises on, last cycle's goals and how far they got,
and the feedback they were given. `goal_facts` hands that over; `draft_goal`
turns each goal the model wrote into a Goal card, in the cycle that is open,
for the person or their manager to approve, change or refuse one by one.

The KRA list, the open cycle's dates and the training catalogue are read
whatever the reader's role:
they are the workspace's own names and dates, not anybody's record, and an
employee who may not open the KRA master still has goals to write against it.
Goals and feedback are read as the person asking.

**Training.** "What would help?" is answered from this workspace's own
training programs and events, against where the latest appraisal says the
person is weakest — not from a catalogue of courses the model has heard of.

Whose goals: your own, your direct reports', or anybody's if you are HR.

### ai_letters.py

OneAI writing an HR letter: a salary certificate, an experience letter.

"I need a salary certificate for the bank" is the most common thing an
employee asks HR in the Gulf, and the answer is the same few facts every time,
typed again. Here the employee asks the panel, the facts come off their own
record, the model phrases them for whoever the letter is for, and the draft
becomes an `Employee Letter` that HR issues by submitting it.

**Facts from the record, words from the model.** `letter_facts` hands over
exactly what the letter may say — dates, designation, salary from the last
slip — and the model is told to use nothing else. HR reads the draft before
it is issued, which is where a wrong figure is caught.

**About yourself, or HR about anybody.** An employee's letter is always about
them; the employee is read from who is asking, never taken as an argument.
HR may name somebody.

### ai_payroll.py

OneAI on a payroll run: what changed against last month, before it is paid.

The comparing is done here, in plain code, and the model is handed the
differences rather than the slips: which amounts moved and by how much is
arithmetic, and a model asked to find them in two hundred slips misses some
and invents others. What the model adds is the sentence — "Rania's net is
down 1,800 because the housing allowance is missing" — and the order, most
money first.

Read as the person asking, so a slip they may not see is not compared: the
salary rules in `one_hr/money.py` apply here exactly as on the list.

### ai_policy.py

OneAI answering a policy question from what this workspace actually says.

"How many sick days do I get?" has two honest answers: what somebody wrote
down (an `AI Knowledge` note, the handbook pasted in) and what the system is
set up to do (the Leave Type's maximum, whether it carries forward). A model
asked without either answers from what companies usually do, which is a
confident wrong answer to the one question an employee acts on.

So `hr_policy` hands over both, each with where it came from, and the tool
says the answer names its source — a note by its title, a rule by its record —
and says plainly when neither covers the question. Read as the person asking.

### away.py

Days the workspace already agreed somebody would not be at work.

An approved `Attendance Request` is the one thing in the product that says, in
advance and in writing, *this person is working somewhere else on these dates*.
The clock's network and place gates exist to catch exactly that shape — off the
office network, outside every location — so without this they would score a
working-from-home Tuesday the same way they score somebody clocking in from a
café they have never been near.

That is the whole of it: read the approval, hand it to `clock._signals`, and let
it drop the four complaints the approval predicted. The attempt still records
what every gate saw, and it now also records *which request* explains it, so the
row reads as an answer rather than as a score nobody can account for.

Nothing here decides anything. A request that was never submitted, or one that
was turned down, or one for a different week, is not an approval and this
returns nothing.

`FORGIVES` is what an approved day predicts, and therefore what it is allowed to forgive.
Everything else the gates raise — an impossible journey, a shared browser, a
missing passkey — is about the person rather than the place, and an approved
request has nothing to say about any of it.

### benefit.py

A benefit application and a benefit claim work out their own limits.

Both doctypes carry a read-only ceiling that their `validate` compares against —
`max_benefits` on the application, `max_amount_eligible` on the claim — and both
are filled only by a whitelisted method their *form script* calls. A document
made any other way has `None` there, and validate does not say so: it reaches

```
if rounded(total_benefit_amount, 2) > self.max_benefits:
```

and raises `TypeError: '>' not supported between instances of 'float' and
'NoneType'`, which names neither the field nor what is missing.

It is the same fault as `leave_balance` on a Leave Application, which read
nought on anything not made through the form, and it gets the same answer: the
method upstream already wrote is called before validate when the field is empty,
so the ceiling is there however the document arrived. Nothing is recomputed for
a document that already carries one, because a submitted application's ceiling
is the one it was approved against.

`application` fills the yearly benefit pot and adds the rows up. `total_amount` and `remaining_benefit` are computed in eleven lines of their
form script and nowhere on the server, so a submitted application read
**Total Amount 0.00** and **Remaining Benefits 0.00** above a table holding
one row of 9,000 against a maximum of 12,000 — three numbers on one screen,
two of them wrong. Adding up a table is not a decision, so it is done here
rather than only where somebody happens to be typing.

### checkin.py

One override on HRMS's `Employee Checkin`, and the reason for it.

`validate_distance_from_shift_location` collects **every** Shift Location
assigned to the employee for that shift — and then checks `[0]`. The list is
built and thrown away, so a company with a depot and four live sites can only
ever have one fence, and whichever row the database happened to return first is
the one everybody has to stand in.

So this subclass checks all of them and passes on any, adds the zones this app
lets a workspace draw, and treats a location marked as a site the way field work
needs: record how far out they were and let them through, because a system that
locks a plumber out at a customer's door is a system they stop using.

Nothing else is touched. The shift resolution, the duplicate window, the
geolocation requirement and the auto-attendance link are all still HRMS's, and
`docs/OVERRIDES.md` carries the line this depends on so an update that moves it
fails a test rather than a screen.

A row written by `clock.py` has already been through One's own gates,
and those answer a question this one cannot: a workspace that says the
network *or* the place will do has said that being on the office line
settles it. Checking the radius again here would overrule that setting
from underneath it. Every other way a check-in is made — the desk
form, an import, HRMS's own app — still comes through the check.

### clock.py

Clocking yourself in and out. The one thing here that writes.

**What makes it safe is that it takes no employee.** There is no argument to
point at a colleague: the row is written for `own.employee_of()` and for nobody
else, so the whole question of whose clock-in this is has one answer that no
caller can influence.

**Which way it points is read, not asked.** The browser does not send IN or OUT,
because a tab open since this morning would send whichever the button said when
it loaded. The direction is the opposite of where the person already is, and
somebody on leave or on a holiday is not offered one at all — a badge-in on
approved leave is a disagreement that writing it would manufacture.

**Everything about the day is HRMS's.** The row goes in as an ordinary document
so its own validation runs: shift resolution, the duplicate window, the
geolocation radius, whatever a workspace has added. No `ignore_permissions` —
the seat's `create` grant on Employee Checkin is the permission, and `own.py` is
not a way around one.

The clock-in endpoint answers in what it returns and never by msgprint, so nothing
may reach the screen except the sentences `told` carries. Anything a gate
or a caught permission check leaves behind would otherwise be merged into
the refusal dialog, which is how "Insufficient Permission for Leave
Policy" ended up on top of a clock-in that was refused for two entirely
different reasons.

`_signals` gathers every doubt raised, with the two rules that are about where somebody is. The network and the place prove the same thing two ways. Either satisfying
it is the sensible default — demanding both means one poor GPS fix stops
somebody working — so where the workspace has not asked for both, a gate
that passed cancels the other's complaint.

An approved Attendance Request comes first and outranks both of them, even
where the workspace did ask for both: the workspace has already said in
writing that this person is working somewhere else today, and scoring them
down for being somewhere else is the gate arguing with its own approval.

`_write` cuts what the check-in's hooks leave in the message log. Anything an `after_insert` hook says is by definition not about whether
the document was accepted, because it was. HRMS's telemetry claims a
milestone row on every check-in and swallows the duplicate in a savepoint
— but the message survives the savepoint, so every clock-in after the
first would put "Duplicate Name" in front of somebody who had just
successfully clocked in.

### closing.py

Closing a day nobody closed.

The commonest cause of a wrong half day is somebody who forgot to clock out, and
`Shift Type` reads the pairs: an IN with no OUT is either a very long day or a
missing row, and the arithmetic cannot tell which. So the shift's end closes it,
sends one nudge, and marks the log as closed automatically rather than leaving
it looking like somebody pressed a button.

Hourly rather than at a fixed time, because a workspace has as many shift ends
as it has shifts, and each one is a time of day rather than a moment.

### decision.py

Somebody answered, and the document says who.

Two doctypes in the Time group are asked for and then answered by a person:
`Attendance Request` and `Shift Request`. HRMS's whole approval for both is that
an Employee has no `submit` grant and HR does, so the decision happens and
nothing records that it was one — no name, no date, no note, and for one of them
no way at all to say no.

What they share is here: who may answer, the three fields that say who did, and
the permission rule. What they do not share stays in their own modules, because
the two verdicts are genuinely different shapes — a shift request carries
HRMS's own `status` and is submitted either way, and an attendance request has
no status field and a turned-down one stays a draft.

**Who may answer is the `submit` grant and nothing else.** Not a role name: a
workspace that has given approvals to its own Department Head role has already
answered that question in the permission table, and a second list of who may
approve is a second answer that will disagree with the first.

### employee.py

What a person's record should answer before anyone clicks anything.

The desk already links thirty doctypes off an Employee, which tells you where
to look and nothing else. This reads the five things somebody opens the record
to find out — where they are today, what leave is left, what is waiting on an
approver, what they are paid under, how long they have been here — and each
answer carries the doctype it came from so the links stay.

Everything here is read through `frappe.get_all` and `frappe.get_doc`, which
apply the reader's own permissions, so the same call answers differently for an
HR manager and for the person themselves. Leave is HRMS's own
`get_leave_details`, because a balance is theirs to calculate and ours to show.

`_standing` is the number `healing.standings()` worked out last night, and its band. The band is read from HR Settings rather than from the constants, so the
colour on the record is the same line the door actually enforces: a site
that refuses below 70 should not paint 65 as unremarkable.

Nothing is returned before the first nightly run has written one. An empty
field is not a score of zero and must not be shown as one.

`get_assignable_masters` stands in for HRMS's question behind the record's
**Create Assignments** menu: is there a leave policy, a salary structure, a
shift schedule to assign. HRMS asks it of all three whatever the reader may
read, so anybody who may open a colleague's record but not Leave Policy got a
permission error on opening it. Ours answers no for a master the reader may
not read, and HRMS then leaves that item out of the menu.

`_days` is a quarter of attendance, one square a day, starting on a week boundary. Nothing marked and no holiday list is a site that does not keep attendance,
and a grid of ninety-odd blank squares says that worse than no grid does.

A day nobody marked is not absent: attendance is written after the fact, and
calling every unwritten day a no-show would be a lie about the person rather
than about the data. Everything Attendance knows about a day rides along —
the shift, the leave type, the hours, whether they were late — because the
square is the only place somebody will ever read it.

`_leave` clears what it caught. A caught PermissionError still leaves its message behind, and a message
nobody cleared is shown on the next dialog this session opens — which is
how "Insufficient Permission for Leave Policy" ended up on top of a
refused clock-in. Catching the exception means we have already decided it
is not the reader's problem, so the sentence goes with it.

### encashment.py

What an encashed day is worth, and saying so before Submit rather than after.

HRMS works the amount out from `leave_encashment_amount_per_day`, a field on the
Salary Structure Assignment or, failing that, on the Salary Structure. Nothing
fills it and nothing asks for it, so on a workspace that has not found it every
encashment reads **0.00** and `before_submit` answers *"You can only submit
Leave Encashment for a valid encashment amount"* — after the form has been
filled in, and without saying which field is missing or where it lives.

So the form says it first, on the record, with a link to the structure it would
be set on. Deriving a rate instead was considered and rejected: a day's pay is
`base / working days` or `base / 30` or the basic component alone depending on
the contract and the country, and a product that guesses pays somebody the wrong
amount without being asked.

### everybody.py

Who works with everybody's records, and so is not kept to their own.

hrms gives every employee a User Permission on their own Employee record (the
employee's Create User Permission box, ticked by default), and from then on
that person sees only what links to themselves: their own timesheets, claims
and leave. Right for most people, and wrong for whoever manages an app. A
project manager could not approve the crew's time, and the books could not
see the timesheets they invoice.

ERPNext's answer is to untick the box. Here it is unticked for whoever People
makes a manager of an app or an administrator of the workspace, and ticked
again when they are neither. It is a rule on the Employee and the User, so it
holds however either is changed: People, the form, a bulk edit or an import.

### expense.py

Answering an expense claim, the same way the other three are answered.

Fourth request doctype in OneHR, fourth approval shape. HRMS gives this one an
`approval_status` Select — Draft, Approved, Rejected — that the approver edits
by hand, and then `on_submit` throws

```
Approval Status must be 'Approved' or 'Rejected'
```

if they forgot, which is a rule the toolbar's own Submit button does not carry.
Attendance Request had no way to say no at all, Shift Request had a dropdown,
Leave Application had a dropdown and a throw; all three now have the same two
buttons, a note, and the three fields that say who decided. This is the last of
them.

`approval_status` stays HRMS's verdict and becomes read-only, because the
buttons set it, and a plain Submit reads as a yes rather than throwing. Their
own `validate_for_self_approval` still runs and still refuses: nobody approves
their own claim, whatever they press.

`before_validate` gives every row the cost centre the company only has one of. `cost_center` is required on each expense row to book the claim, and it is
filled by their form script — from the claim, which is filled from the
company. A claim made any other way fails on submit with *"Row 1: Cost
Center is required in the expenses table"*, which is a better message than
most of the ones in this audit and still a field nobody typed because there
is only one answer.

### gates.py

The three gates, each answering rather than throwing.

Nothing here refuses anybody. Each gate reports what it saw and which signals it
raised, `clock.py` adds them up, and the score decides. That split is what lets
the same code run in a workspace that enforces every gate and in one that only
watches, and it is why the ledger records the same fields either way.

The order they run in is about cost, not importance: the passkey first because
nothing else means anything without knowing who, then the network because it is
one string comparison with no prompt, then the place, which needs the
employee's permission and a second or two for a fix and should not be paid for
by somebody whose passkey already failed.

### growth.py

Two things the appraisal machinery expects somebody to do by hand.

**A cycle nobody set to In Progress is invisible to its own summary.** An
Appraisal Cycle is born `Not Started`, and the only thing in HRMS that ever
changes that is `complete_cycle`, which sets `Completed`. Nothing sets
`In Progress`. But the summary the cycle screen shows is looked up by it:

```
if not cycle_name:
	cycle_name = frappe.get_value(
		"Appraisal Cycle", {"status": "In Progress"}, order_by="start_date desc"
	)
```

So "employees without feedback" is counted against no cycle at all until
somebody notices the dropdown and changes it. Creating appraisals for a cycle is
the moment it starts, so that is where the status moves.

**An appraisal has no period, so its duplicate check has nothing to compare.**
`validate_duplicate` looks for another appraisal for the same person either in
the same cycle *or* over an overlapping period:

```
(Appraisal.appraisal_cycle == self.appraisal_cycle)
| ((Appraisal.start_date.between(self.start_date, self.end_date)) | ...)
```

Nothing in HRMS ever fills `start_date` or `end_date` on an Appraisal — not
`create_appraisals_for_cycle`, not the form script — so every comparison in the
second half is against NULL, which is never true. Only the cycle branch ever
fires, and two appraisals for one person in two different cycles covering the
same months go through. The cycle knows the dates, so the appraisal takes them.

**A promotion says who and when and nothing about what changed.** The new
designation lives in a `promotion_details` row, which is a child table and so
cannot be a list column and cannot be searched. `one_becomes` is that row's
`new` value, kept on the document, so the list can say `Engineer → Senior
Engineer` and a filter can find every promotion into one grade.

### heads.py

What OneHR's pages say above their fields. See one/head.py.

A person's page, first. Where they are right now as the title's pill; a quarter of attendance as a
heat map of named days; and beside it the handful of numbers somebody opens
the record to read: their standing, their last check-in, what leave is left
of each type, what is waiting on an approver, what they hold and what they
are paid under. The figures are employee.py's `overview`, worked out once per
request with the reader's own permissions.

Then the requests and the documents. A request somebody answers (leave, an
attendance correction, a shift, an expense claim) carries Approve and Reject,
each asking for a note and saying what it will do; and every one of these
records opens on a sentence saying what it comes to, which the fields it
opens on do not: how many days of what, what a slip pays, how far a vehicle
went on how much. A sentence that reads a field the form can change redraws
as it changes (`redraw_on`), so it is right before the record is saved.

### healing.py

What the system teaches itself, and the one rule that keeps it safe.

A router reboots, an office takes a second line for the 5GHz band, a warehouse
registered at its office door has everybody clocking in at the gate two hundred
metres away. Today each of those locks people out on a Monday morning and needs
somebody to edit a settings box. Here they become proposals.

**Only a clock-in that was already corroborated another way may teach anything.**
Three colleagues in a café cannot promote the café, because none of them was
inside a fence or on a known network when they voted. And **nothing heals
towards less security**: a proposal can widen *where* people may clock in, never
*who* may. Credentials, employees and standing are never promoted automatically.

Run nightly rather than on every clock-in. A proposal is a claim about a
pattern, and a pattern is not visible from inside one request.

### hiring.py

OneAI on the hiring walk: every applicant read, rated and placed.

**One call per applicant.** The CV is read against the opening's criteria and
the new applicant is placed among everybody else still in the running in the
same call — the model is handed the pool as a line each, never a CV twice.

**Everything here runs as OneAI.** A job made by a web-form applicant would
otherwise run as Guest, and one made by an HR user would write comments in
their name that they never wrote. `AUTHOR` is a disabled user with the OneAI
mark as its picture: the timeline says who spoke, and nobody can sign in as it.

`PART_SECONDS` is how long one part of a recording is. The recorder restarts on this beat so
each part is a whole file: uploaded as soon as it closes, transcribed as
soon as it lands, and small enough to send — opus at 24 kbit/s is under a
megabyte for five minutes. It is said again in public/js/hiring.js.

### learned.py

Settling something the clock proposed.

`healing.networks` and `healing.zones` write a `Clock Network` or a `Clock
Place` as Proposed on the first corroborated sighting and promote it to
Confirmed once enough employees agree. The two states a person decides between
are the same on both doctypes, so the verbs are here rather than twice.

Status is read only on those records. It was a dropdown, which made rejecting
a proposal look like picking a value from a list, and let somebody set a
rejected address back to Confirmed without saying why. A rejection is final in
the sense that matters: `healing._learn` matches a Rejected row like any other
and never promotes it again.

### leave.py

Answering a leave application, the same way the other two are answered.

Three doctypes in OneHR are asked for and then answered by a person, and until
now each had its own shape. Attendance Request had no way to say no at all;
Shift Request had a Status dropdown; this one has a Status dropdown too, and
`on_submit` throws "Only Leave Applications with status 'Approved' and
'Rejected' can be submitted" — a rule the toolbar's own Submit button does not
carry. Three shapes for one question is two too many.

So it gets what the other two got: Approve and Reject, a note, and the three
fields that say who decided and when. HRMS's `status` stays the verdict and
becomes read-only, because the buttons set it, and a plain Submit reads as a yes
rather than throwing.

The headline is the other half. HRMS stacks two — frappe's "Submit this document
to confirm" and its own "Submit this Leave Application to confirm." — and
neither says what approving does. The one here says how many days of what, for
whom, and what it leaves them with, because the table above it does not: it
shows Available Leaves 21 beside Leaves Pending Approval 3, and the 3 is the
application you are looking at.

`PAID_AS` is what an encashed day is paid as. HRMS ships Casual Leave with
`allow_encashment` on and no earning component, and `create_additional_salary`
throws "Please set Earning Component for Leave type" on *submit* — after the
form has been filled in and the days worked out. The component it is pointed
at is one HRMS installs itself, in `payroll/data/salary_components.json`.

### leaving.py

The last day, and what stops on it.

Setting a Relieving Date is what HR does when somebody leaves, and on its own
it does almost nothing: attendance stops counting past it, `Exit Interview`
refuses without it, and the shift assignment tool filters on it. It does not
set the status, so the login keeps working, the passkey keeps clocking in, and
the roster keeps listing them — and the first thing that objects is payroll,
weeks later, with "Employee {0} relieved on {1} must be set as 'Left'".

So the date does the obvious things here. The status is the lever the framework
already wired: erpnext's `update_user_status` disables the User the moment an
employee stops being Active, so setting the status is also what takes the login
away. The passkey and the shift assignments are ours.

It runs twice — when the record is saved, and nightly for a date set in
advance that has since arrived — because a last day is usually typed before it
happens.

### ledger.py

Every clock-in tried, written down whether it was allowed or refused.

`Employee Checkin` only records successes, and the refusals are the interesting
ones. So each attempt writes a `Clock Attempt` of its own carrying what every
gate saw, and that table is three things at once: the review queue, the evidence
when somebody disputes a day, and what the self-healing reads.

The row is written last and always, including when a gate refused and including
when writing the check-in itself threw. A ledger that is only written on the
happy path is a ledger of the wrong half.

The attempt is committed when it is written rather than with the rest of the request, because the next
thing that happens may be HRMS refusing the check-in and a rollback. The
ledger row is the record of the attempt and must not share the fate of
what the attempt went on to try.

### letter.py

An appointment letter carries the template it was told to use.

`introduction` and `terms` are both required on an Appointment Letter, and both
are filled by eleven lines of their form script when somebody picks a template:

```
frm.doc.terms = [];
... frm.add_child("terms"); ...
```

Nothing on the server does it, so a letter made any other way — an import, an
API, the onboarding automation a workspace writes for itself — is refused with
`MandatoryError: [Appointment Letter, HR-APP-LETTER-00001]: terms`, naming a
table it cannot see how to fill.

It is the fourth instance of the same fault in this audit, after
`leave_balance`, the two benefit ceilings and the expense claim's cost centre,
and it gets the same answer: the template is read, on the server, before
validate, when the fields are empty. A letter that already carries terms keeps
them, because somebody edited them deliberately.

### lifecycle.py

Two things that refuse the first onboarding a workspace submits.

**The holiday list.**

`Employee Boarding Controller.get_holiday_list` decides which days the boarding
tasks may not land on:

```
if self.employee:
	return get_holiday_list_for_employee(self.employee, as_on=self.boarding_begins_on)
else:
	if not self.holiday_list:
		frappe.throw(_("Please set the Holiday List."), frappe.MandatoryError)
```

An Employee Onboarding is for somebody who **is not an employee yet** — creating
them is what the record is for, and `make_employee` is what does it. So
`self.employee` is empty on every onboarding that has not been completed, and it
falls to `self.holiday_list`, a field on the document that nothing fills: not
the form script, not `validate`, not the template the activities came from. The
company's `default_holiday_list` is sitting right there, correctly set by the
setup wizard, and is never consulted.

Employee Separation takes the other branch and works, because the person leaving
is an employee and `get_holiday_list_for_employee` falls back to their company
on its own. So it is an asymmetry rather than a decision.

This is the fifth instance of the fault this audit keeps finding — after
`leave_balance`, the two benefit ceilings, the expense claim's cost centre and
the appointment letter's terms — and the worst of them, because the other four
were filled by a form script and this one is filled by nothing at all.

**The project it starts on the wrong day.** Past that, `on_submit` makes a
Project for the boarding and a Task per activity:

```
"expected_start_date": self.date_of_joining
if self.doctype == "Employee Onboarding"
else self.resignation_letter_date,
```

while every task starts from `add_days(self.boarding_begins_on, activity.begin_on)`.
Onboarding *is* the work done before somebody joins — the contract, the laptop,
the induction — so `boarding_begins_on` is earlier than `date_of_joining` on any
realistic record, and ERPNext's own Task guard then refuses the first task:

```
TASK-2026-00003's Expected Start Date cannot be before PROJ-0002's
```

The project is given the day the person arrives, which is when onboarding
*ends*. A boarding project starts no later than its first task, so that is what
`task` in `lifecycle.py` settles, and only for a project a boarding document owns.

### marking.py

Marking a day by hand, for the days the clock did not answer.

hrms's Employee Attendance Tool lists everyone with no Attendance row on a date
and writes one for whoever is ticked. It does that well; the one thing it never
reads is the ledger next to it. `clocked_in` answers who has an IN log on the
date, so a day that is half clocked and half asserted is not retyped.

A log a reviewer rejected in the review queue carries `skip_auto_attendance`
and is left out, so refusing a check-in there also keeps it out of the marking.

Overtime is not here: it belongs to one employee on one day rather than to a
list, and lives in `one_hr/overtime.py`.

### money.py

Nobody is asked what currency they are paid in.

One workspace is one company, and a company pays in one currency — the one on
the Company record. Every payroll and HR doctype carries a `Currency` Link
anyway, twenty-two of them, and on a single-company site every one of them shows
the same three letters beside an amount that is already formatted in them.

**Only the ones nobody types are hidden.** A `read_only` currency or one with a
`fetch_from` is filled by the framework or by their own controller, so hiding it
cannot stop a document being saved — that is the whole test, and it is checked
against the schema rather than assumed. Fourteen of the twenty-two qualify.

What stays visible, and why:

* **Salary Structure** declares the currency the assignments and slips fetch
  from. It is the root of the chain and the one place the answer is given.
* **Job Applicant**, **Job Opening** and **Job Opening Template** quote a salary
  range on an advertisement, which is a thing a workspace may genuinely want to
  write in somebody else's currency.
* **Employee Tax Exemption Declaration** and **Proof Submission** are neither
  read-only nor fetched, but their own form script fills the field from
  `get_employee_currency` when the employee is chosen. They are named in `ALSO`
  in `money.py` rather than found by the rule, because the rule reads the schema and
  this answer is in a `.js` file.
* **Payroll Entry** is hidden by its own customization instead, because it is
  neither read-only nor fetched — their form script fills it from the company,
  which was checked in the browser rather than read off the schema.

Derived from the site rather than shipped as a fixture, for the same reason
`one/company.py` is.

### names.py

An employee link says the person's name, so nothing has to repeat it.

Frappe already knows how to show a link by its title: set
`show_title_field_in_link` on the doctype and every link to it — on a form, in
a grid, in a list, in a printed document — reads the title instead of the id.
Employee has a title field (`employee_name`) and had the switch off, so every
link to it read `HR-EMP-00004` and erpnext's answer was to hang a read-only
`Employee Name` beside it, fetched from the same record.

That is fifty-odd doctypes each saying the same thing twice:

```
Employee      HR-EMP-00004: Tarek Nassar
Employee Name Tarek Nassar
```

The switch is set in `one_hr/custom/employee.json`, and this sweeps away the
mirrors it makes redundant. Only fields that are literally `fetch_from` the
link are touched — a mirror by definition, kept in step by the framework rather
than typed — and only on parent doctypes, because in a grid the mirror *is* the
column somebody reads.

A list keeps its name: `employee_name` is the title field on almost all of
these, and a list's title column is drawn from the doctype's `title_field`
rather than from the field being visible. Where it is not the title field and
is `in_list_view`, it is left alone — `Goal` is the one such row — because
hiding it there would take the person's name off the list and put nothing back.

The other half is the list column. Where `employee_name` is the title field the
list already opens with the person's name, and the `employee` column beside it
now reads the name too, because the link renders its title. So a Salary Slip
list said *Rania Sabbagh · Draft · Rania Sabbagh*. That column comes off — but
only where the title is the name, because everywhere else it is the only place
the person appears.

Derived from the site rather than shipped as a fixture, for the same reason
`one/company.py` is: the set of doctypes depends on which apps the site
carries, and only the site knows that.

### overtime.py

Overtime, recorded on the day it was worked.

Overtime lives on the Attendance row: `overtime_type`, `actual_overtime_duration`
and `standard_working_hours`. A shift writes them from the check-ins when it
processes the day; `record` writes the same three when nobody clocked out, from
a dialog on the Employee or on the Attendance itself. Either way Overtime Slip
collects them later without knowing which hand wrote them, which is why there
is one place to record overtime rather than two.

The fields are read only on the form, and the row is already submitted by the
time anybody notices the overtime, so `record` writes them straight to the row
and leaves a comment saying who did it. Nothing downstream of Attendance is
posted at submit, so there is no ledger to disagree with.

`no_double_pay` is the other half of having one place: Overtime Slip lets a row
be typed with no Attendance behind it, and a period holding both would be paid
twice.

The rest of `overtime.py` is the slip itself. Three things about HRMS's screen are
worth knowing before reading it:

**Its Fetch button saved the document.** `get_emp_and_overtime_details` ends in
`self.save()`, so pressing Fetch on a new form inserted a real slip and left the
person looking at the unsaved blank one — press it twice and it answers that
"Overtime Slip: HR-OT-SLIP-00001 has been created" about a record nobody
knowingly made. `collect` reads the same attendance and *returns* it; the form
fills the grid and the person saves when they mean to.

**It never said what it would pay.** Everything on the screen is hours, and
submitting writes Additional Salary from the type's rate and multipliers. The
amount is worked out before the save and written onto the slip, using HRMS's own
`get_overtime_component_amounts` rather than a second copy of the arithmetic.

**It refused a slip for anybody with no salary structure**, because the only
thing it wanted the structure for was the payroll frequency that sets the two
dates. `dates` falls back to the calendar month, which is what a fixed hourly
rate needs and all it ever needed.

### own.py

Who the reader is here.

The Employee whose `user_id` is the session's user, and nothing else. Not a
match on email, which is one line shorter and hands somebody their namesake's
record on any workspace where two people share a personal address, and not a
match on name. A reader with no such row is nobody here — which is a workspace
that has not linked its logins, and the fix is a field on a record.

Everything that writes a clock-in reads the employee from here rather than
taking one as an argument, which is what makes those endpoints safe: there is no
value a caller can send that points at a colleague.

### passkey.py

Who pressed the button, proved by the phone that holds their passkey.

A passkey is a key pair the phone makes and keeps in its secure hardware or its
keychain. Registering one is a prompt; using one is Face ID, a fingerprint or
the device PIN, and every call here asks for `user_verification="required"` so
that happens on every clock-in rather than only the first.

**One credential per person**, kept on their login (`user`) so somebody with no
employee record can sign in with one too. For an employee the clock checks, a
second needs HR to reset the first, and `remove` refuses them; anybody else
removes their own. That rule is the gate. A colleague who knows your password and signs in as you on
their own phone finds no passkey there and cannot make one, so they cannot clock
in as you; the only way through is your actual phone with your face or PIN.

**The credential id is the device identity.** It is stable, it is cryptographic,
and unlike a cookie it survives clearing browser data and is not stepped around
by a private window, because it lives in the operating system's keychain rather
than in the browser profile. There is no cookie here and there was never a good
reason for one.

Verification is `py_webauthn`'s. Writing CBOR parsing and COSE key handling
ourselves would be security-critical code with no reason to be ours.

### policy.py

What this workspace has asked for, read from HR Settings in one place.

Every switch in `policy.py` is a Custom Field this app adds to HRMS's own single
doctype, which is where a tenant already goes to configure HR. The reason they
are all read through here rather than with `get_single_value` scattered about:
a default typed twice is a default that will disagree with itself, and a gate
that cannot be found from one file is a gate nobody can audit.

A Single stores nothing until somebody saves it, and `get_single_value` casts a
missing Int or Check to zero rather than to None. So a default of 1 would read
as off on a site nobody has opened HR Settings on, which is how every gate would
have been silently disabled on a fresh install. `seed()` writes each default
once, at install and after every migrate, and only where the field has never
been written — so it can never overrule what a tenant chose.

### presence.py

Where somebody is, right now.

The question every HR product is opened for and none of them answers on the
page you are already on: *is this person in today?* HRMS holds the answer across
four doctypes and shows it in none of them — Employee Checkin is a log, Attendance
is a day's verdict written after the fact by a scheduled job, Leave Application
is an approval, and the Holiday List is a calendar. A person asking "is Omar
here" has to open three of those and do the reasoning themselves.

So this does the reasoning once, in the order the answers actually rank:

```
on leave    an approved Leave Application covering today
holiday     today is in the shift's or the company's Holiday List
in          the last check-in today was an IN
out         the last check-in today was an OUT
absent      Attendance marked them so, and nothing above said otherwise
unknown     none of the four has anything to say
```

Ranked rather than merged, and leave first, because the four disagree all the
time and the disagreement is not an error: somebody on approved leave who badged
in to collect a laptop is *on leave*, and a product that says "in" because a
turnstile said so is a product that gets somebody's pay wrong.

`late` is not a state, it is a fact about an `in`. Somebody who arrived at 09:40
against a 09:00 shift is here — they are simply here late, and making that a
separate state means a strip of faces cannot count how many people are in.

**This reads. It never writes.** Auto-attendance is HRMS's job and it runs on a
schedule; a page that marked somebody present because it happened to be open
would be a second writer on the same rows with no lock between them.

### request.py

Asking for a day to count as worked, and the person who answers.

HRMS ships the asking and not the answering. `Attendance Request` is a
submittable document whose submit writes the Attendance rows, and the whole of
its approval is that an Employee has no `submit` grant and HR does — so the
decision happens, but nothing anywhere records that it was a decision, who made
it, or that anybody ever said no. A request turned down is a draft nobody
reopened.

So three things are added and nothing is replaced. Submitting is still what
writes the attendance, and it now also writes down who approved it and when.
Rejecting is a verb: the request stays a draft, carries a `Rejected` decision
that only somebody with the submit grant can set, and cannot be submitted while
it stands. And the reason stops being two hardcoded words.

**The reason is a record now, but HRMS's field is still the one that decides the
status.** `AttendanceRequest.get_attendance_status` reads `self.reason` and
compares it to the literal string "Work From Home"; everything else becomes
Present. Rather than override that method, `before_validate` writes HRMS's own
field from the chosen `Attendance Reason` — so a workspace can offer fifteen
reasons and HRMS keeps marking the days exactly as it always did.

### review.py

What happens to a check-in nobody could be sure about.

`HR Settings` says a check-in scoring between the two thresholds is "written,
and marked Flagged for review". Written it was; reviewed it was not — there
was no queue, no verdict, and nobody was told. The band in the middle is the
whole reason for having two thresholds rather than one, so it needs an end.

Rejecting does not delete anything. The log stays, the attempt stays, and the
check-in gets `skip_auto_attendance`, which is HRMS's own lever for a log that
should not count towards a day's attendance. What was attempted and what was
decided both remain readable, which is the point of keeping a ledger at all.

### rules.py

The arithmetic behind a clock-in, with nothing of Frappe in it.

Everything above `rules.py` — reading a Shift Location, writing an attempt, deciding who
may — is in the modules that do import frappe.

`SIGNALS` holds the signals, their weight, and the sentence the employee reads. A weight is how
much the signal takes off the score, out of a hundred. Nothing here is
learned: a refused check-in has to name what was wrong, and a number nobody
can explain cannot be named.

The dividing line is refuse on what is certain and flag on what is a guess,
so the two that are certain — the wrong network, and outside every location —
are weighted to refuse on their own, while everything probabilistic sits
under the flag band and needs company to get past it.

`N_` marks the sentence for extraction without importing frappe, which this
module must not do. `clock.py` translates it at the point it is shown.

`REFUSE_BELOW` and `FLAG_BELOW`: below the first a clock-in is refused outright; below the second it is written and
flagged. Both are overridable per workspace, and both are deliberately far
apart: the middle band is where a human looks, and a system with no middle
band is one that argues with its own staff at the door.

`TOP_SPEED` is how fast somebody may travel between two clock-ins before the distance stops
being possible, in metres per second. 55 is about two hundred kilometres an
hour — fast enough that a train or a motorway never trips it, slow enough
that two cities in ten minutes does.

`PHONES` is what a mobile browser says about itself. Not a security control — a caller
can send any user agent they like — but somebody who forges one to enrol a
passkey on the office PC has gone out of their way to weaken their own
credential, and the machine they did it on shows up in the ledger anyway.

### setup.py

What a shift needs before a check-in ever becomes a day.

hrms turns `Employee Checkin` pairs into `Attendance` from one scheduled job,
and `ShiftType.has_incorrect_shift_config` makes that job return without a word
unless the shift has three things: auto attendance on, a date to process after,
and a last sync. A workspace missing one gets an empty Attendance list, empty
charts, an empty Overtime Slip and no error anywhere — the clock keeps taking
check-ins and nothing reads them.

So the three are set by the setup wizard, checked nightly against the shifts
that actually have check-ins, and offered as one button on the Shift Type form.

`auto_update_last_sync` is the fourth. Without it `last_sync_of_checkin` stays
where it was set and attendance quietly stops being processed past that moment;
with it hrms moves it forward every hour.

### shift.py

Asking to work a different shift, and the person who answers.

Three things were wrong with HRMS's screen and all three are the same kind of
thing: the form knows something the person reading it does not.

**The approver picker comes back empty and does not say why.** `Approver` is
mandatory and HRMS filters it to exactly two sources — the employee's own
`shift_request_approver`, and the `shift_request_approver` rows on their
department. An employee with neither gets an empty list, a required field, and
no way to find out what is missing. So the form fills the field itself where
there is one obvious answer, and says what to do where there is none.

**Nothing on the screen said what the shift is.** The whole document is about
moving somebody onto "Evening", and "Evening" is a name. The hours are written
onto the record so the form and the list both read as a sentence.

**Submitting was the approval and refused to say so.** HRMS's `on_submit`
throws unless `status` is already Approved or Rejected, which is a rule the
toolbar button does not know about, and either way nothing recorded who
decided. Approve and Reject set the status, sign the document and submit it —
rejecting closes the request and writes no Shift Assignment, which is HRMS's
own behaviour and the right one.

### signin.py

Signing in with the same passkey somebody clocks in with.

An employee who only ever clocks in has no reason to hold a password, and a
password they never type is a password they write down. The credential is
already discoverable — `start_registration` asks for a resident key — so the
browser offers the account and nothing is typed at all.

**This is the only place in One that logs somebody in**, and it does it through
`frappe.local.login_manager`, which is the same path the password form takes:
the session, the login hooks, the rate limiter and the audit trail are all
frappe's. Verifying a signature and then setting a session by hand would be a
second way into the product, and a second way in is the one thing a login page
must not have.

### home.py and story.py

OneHR's Home is the `onehr` page (`page/onehr`, `frontend/src/home/HrHome.vue`),
as OneCRM's is `onecrm`; the workspace it replaces went with
`patches/home_is_a_page`. It is everybody's, not only HR's, so it reads twice:

- `home.read` is the reader's day, for anybody: their own requests still
  waiting, the leave they have left, the requests waiting on them as an
  approver (or, for HR, those with no approver named, which HR answers), and
  for HR the flagged check-ins, documents expiring and contracts or
  probations ending within a month, and today's interviews. Then the
  directory, each row called what it opens.
- `story.read` is HR's only, and None for anybody else, since how many people
  work here and what they cost are not theirs to read: the headcount month by
  month, who joined and left, attendance over thirty days, leave taken, the
  payroll, expense claims and the hiring funnel, in the company's currency.

Home is a place (`onehr_home.shown`), so an extension may add a note or a
button, and OneAI is told what it shows (`ai.page`). HRMS's own phone app at
`/hrms` is a second self-service, unbranded and reading approvals from PWA
Notifications One never writes, so it opens this Home instead
(`website_redirects`). A rail's JSON is synced
only when its `modified` changes, so the rail's own date moved with it.

### tell.py

What HRMS tells people, told through One's hub instead (docs/NOTIFICATIONS.md, stage 6).

HRMS tells people things four ways, and none of them is the bell:

- **Approvals** go to its own phone app, as PWA Notification rows nobody here
  reads (`PWANotificationsMixin`): somebody asks for leave, an expense or a
  shift, and the approver is told; it is answered, and the employee is told.
  The classes in `tell.py` tell the same moments through the hub instead,
  one type per request and per answer, so HRMS's phone app gets none of them.
  An answer carries the approver's note (`note`). Leave also mailed both moments
  from Email Templates set in HR Settings (`send_leave_notification`); that
  switch is off, and hidden, because this tells them now.
- **Reminders** are mailed by its scheduler: birthdays, work anniversaries,
  upcoming holidays, an interview soon, feedback not given. Each has a switch
  in HR Settings; those are off and hidden (`replaces` in notifications/one_hr/),
  and the jobs here tell the same people the same things, in the morning. A
  type starts on only if its switch was on. HRMS compared an interview's date
  as though it held the time, so its reminder fired at midnight and its
  feedback reminder almost never; ours compare the interview's start and end.
- **A rescheduled interview** is mailed to interviewers and applicant alike,
  in fixed words, with no switch. `Interview.reschedule_interview` is
  HRMS's, written again here (HRMS is GPL-3.0, this repository AGPL-3.0) so
  the interviewers are told in One and the applicant is mailed in a type's
  words.
- **Mails that are the point** stay HRMS's: a payslip, the exit
  questionnaire, and the report of earned leave that failed to allocate. They
  are listed as types with `mailed_by`, so the administrator sees them.

A person with no user here cannot be told in One; only an interview's
applicant is mailed, in the type's words. A birthday is only told to people
with a user, and opens nothing, since most colleagues may not open somebody
else's employee record.

OneHR's own moments, besides HRMS's:

- **Attendance Request Asked and Answered**: a request waits, to HR; its
  answer, with the note, to the employee (`attendance_asked`,
  `attendance_answered`).
- **Letter Requested and Letter Issued**: asked of HR, issued to the employee.
- **Grievance Raised**: to the people trusted with grievances, for every
  grievance; a Sensitive or Urgent Grievance follows when OneAI reads one as
  that. **Grievance Answered**: resolved or found invalid, to whoever raised it.
- **Document Expiring**: a passport, visa or permit a month and a week from
  expiring, to the employee and HR, each morning.
- **Passkey Reset Asked and Done**: an employee who changed phones asks HR,
  with what the phone said, and is told when they can register the new one.
- **Interview Scheduled**: to its interviewers, the day it is made, and to
  an interviewer added later; the applicant is mailed the time.
- **An approval with no approver**: hrms lets leave, an expense or a shift go
  without one, and does by default, so the Asked type then goes to HR. An
  approver named or changed while it waits is told then. Leave the employee
  cancels after it was decided is told to the approver (Leave Cancelled).
- **Contract Ending and Probation Ending**: a month and a week before, to HR
  and the employee's manager, each morning.
- **Check-in Rejected**: a flagged check-in HR turned down, to the employee.
- **Marked Absent**: a working day the shift marked absent on its own, to the
  employee, who may have forgotten to clock in.
- **Leave Expiring**: leave that does not carry forward, two weeks before it
  lapses unused.
- **Appraisal Started**: to the employee, when a cycle makes their appraisal.
- **Job Requisition Asked and Answered; Referral Received and Answered**: to
  HR, then back to whoever asked or referred. A referral's answer comes from
  its Job Applicant, since hrms sets the referral's status there by db_set.
- **Expense Claim Paid**: a payment that settles a claim, to the employee.
- **Employee Details Changed**, sent from one/tell.py: an employee's own
  change to their record, to HR. Exit Interview Scheduled and Training
  Scheduled are hrms's rules, carried (one/rules.py).

`place_proposed` is one notification, to the people who can undo it. Told rather than asked: the row is already Confirmed and already working, on
the reasoning that a Monday morning where nobody can clock in is worse than
a place on the list that HR can reject at nine. A change nobody was told
about is what makes a self-healing system feel haunted, so it is told.

`check_in_flagged` sends one alert per flag, to everybody who can settle it. The reasons go in the notification rather than only on the record, because
a flag worth raising at all is worth being able to judge from the phone
that buzzed.

### timesheet.py

Hours, written the way somebody reads them back.

One thing here is not cosmetic. ERPNext's timer offers to *resume* any row whose
Completed box is unticked and whose From Time is in the past — which is every row
anybody typed by hand, because nothing ticks Completed when you enter a block
yourself. It then counts from that row's From Time, so a 09:00–13:00 block
entered yesterday opens the timer at fifteen and a half hours, and pressing
Complete writes `to_time = now` over the end time that was already there. Four
hours becomes fifteen, silently, on a document payroll reads.

The fix is in `public/js/timesheet.js` and it is small: a row with a To Time is
finished, so the only row the timer may resume is one that has a start and no
end. What is here is the reading half — `one_when` on each row, so the grid says
"21 Sep 09:00 – 13:00" instead of a truncated datetime and a number of hours
with no end beside it — and its title. ERPNext's Profit on Billed Hours names
the person by a timesheet's title, which only its form ever filled, so a
timesheet made by a timer, an attendance or OneAI named nobody. `title` fills
it with the employee's name, or its maker's, on every save
(one_project/patches/timesheets_titled.py did the ones made before).

### report/attendance_by_shift/attendance_by_shift.py

Every day that was marked, against the shift it was meant to be.

HRMS's `Shift Attendance` showed one row where the month held twenty-seven,
and said nothing about the twenty-six it dropped. Two inner joins did it:

```
.inner_join(shift_type).on(attendance.shift == shift_type.name)
.inner_join(checkin).on(checkin.attendance == attendance.name)
```

The first throws away every Attendance with no shift on it — which is most of
them on a site that marks attendance by hand or runs one unassigned shift. The
second throws away every day with no `Employee Checkin` pointing at it, and the
checkbox that puts those back ("Include Shift Attendance Without Checkins") is
off by default and reads like it adds something extra rather than restoring what
was cut.

A number that has quietly discarded its own denominator is worse than no number:
"Late Entries 0" looked like nobody was late and meant twenty-six days were never
counted. So every join here is a left join, every day in the period is a row, and
a day with no shift says so with an empty cell.

The arithmetic is still theirs — `update_late_entry` and `update_early_exit`
know about grace periods and this does not re-derive them — and it is only
applied to the rows that have a shift window to measure against.

`_totals` counts days, not "records" — the same number, and one of them is a word people say. The four status tiles add up to the rows, which is the whole point: a count
that has silently dropped its own denominator is what was wrong here. Working
from home counts as present, the way HRMS's own summary counts it. Half days
and leave only appear when there are some, because five tiles fit on one line
and two permanent zeroes are not worth the second.

`No Shift` is the one that would have explained the old screen: nineteen of
these twenty-seven days carry no shift, which is exactly what its inner join
threw away without saying so.

### report/hiring_pipeline/hiring_pipeline.py

Every opening, everyone who applied to it, and how far each one got.

HRMS's `Recruitment Analytics` builds its rows from Staffing Plans:

```
staffing_plan_details = get_staffing_plan(filters)
staffing_plan_list = list(set([details["name"] for details in staffing_plan_details]))
sp_jo_map, jo_list = get_job_opening(staffing_plan_list, filters)
```

An opening with no `staffing_plan` on it is not in `jo_list`, so its applicants
are never fetched and its offers never counted. Staffing plans are optional —
nothing in hiring asks for one, and most workspaces never make one — so the
report answers "nothing is happening" on a site that is hiring four people. It
is the same fault as `Shift Attendance`: a measurement built out of the records
that happen to exist rather than out of the thing being measured.

So this starts from the Job Opening, which is the record hiring actually turns
on, and left-joins everything else. An opening nobody has applied to is a row
that says so, because "nobody applied" is the answer somebody opened this to
find. The staffing plan is a column, not the spine.

The counting is deliberately one row per applicant rather than a tree: a tree
whose parent rows are blank in nine columns reads worse than a flat list, and
it cannot be sorted or exported by the column somebody cares about.

### report/hours_utilization/hours_utilization.py

How much of everybody's week ended up on a timesheet.

HRMS's version of this is the third report in the Time group to answer a
narrower question than the one it is opened for, and the first where the
narrowing makes every percentage on the screen wrong.

**Its denominator counts weekends.** One line does it:

```
TOTAL_HOURS = flt(self.standard_working_hours * self.day_span, 2)
```

`day_span` is `(to_date - from_date).days` — calendar days. Over 22 August to
22 September that is thirty-one, so a person's available hours came out as
8.5 x 31 = 263.5, which assumes they were meant to work four weekends and every
public holiday in between. Here the available hours are working days only, per
employee, from the holiday list actually assigned to them.

**Only people who filled a timesheet in were on it**, so the one number the
report exists to surface — somebody at nought — was the one it could not show.

**And drafts counted.** There is no docstatus filter, so hours nobody has
submitted were in the totals. They are out of the columns now and in a tile of
their own, because "why is this so low" is usually answered by them.

Two smaller ones. A timesheet whose start and end both had to fall inside the
range was dropped whole when it straddled the boundary; the rows are filtered on
the log's own time instead, so a week spanning the first of the month counts the
days that belong to the period. And the summary averaged percentages across
whoever happened to log time, which rises as fewer people fill theirs in; it is
one division of totals now.

### report/monthly_attendance/monthly_attendance.py

One month, one row each, everybody on it.

HRMS's `Monthly Attendance Sheet` answers a narrower question than the one people
open it for, in three ways that compound.

**It keys on employee *and* shift**, so somebody who picked up a shift assignment
mid-month becomes two rows — one blank-shift, one "Day" — with half their days on
each and neither being their month.

**It only shows people who have an Attendance row.** Six active employees, three
rows: anybody with nothing marked at all is not on the sheet, which is exactly
the person the sheet exists to find. `unmarked_days` in the summarized view has
the same hole, because the query it sums returns nothing for them.

**And it asks which company**, with an Include Company Descendants checkbox
underneath. One workspace is one company; see `one/company.py`.

So the rows are built from HRMS's own pieces — its attendance map, its holiday
map, its status abbreviations — and the three questions above are answered before
they reach it. Nothing here re-implements what a day means.

The chart is gone rather than replaced. Attendance Overview is where the shape
of a month is looked at; this is the sheet somebody prints and initials, and a
three-series line of counts between nought and three, with every date label
rendered as an ellipsis, was a third of the screen in front of it.
