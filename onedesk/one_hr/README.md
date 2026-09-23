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

- **Home** — the page an employee starts their day on, with Check in, Request
  leave, Claim an expense and Payslips.
- **Overview** — who is in, who is absent, who is on leave, and flagged
  check-ins waiting for a look.
- **Employee**, **Org Chart**, **Setup**.
- **Time**, **Leave**, **Pay**, **Tax & Benefits**, **Expenses**, **Hiring**,
  **Growth**, **Joining & Leaving** — one group each, opened with the arrow.

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

## Clocking in

Employees clock in and out themselves from any phone or computer. There is no
machine to buy.

**The control in the rail.** A dot beside the rail's other icons: green while
you are clocked in, grey while you are not. Hover to see today's hours; click
to clock in or out. It picks the right direction itself, and it does not
appear for somebody on leave or on a holiday, for anybody without an employee
record, or when the workspace has not turned self check-in on.

**Before the first clock-in, register a passkey on your phone.** It is a key
your phone keeps and unlocks with your face, fingerprint or PIN. Registering
has to be done on a phone, not a desktop computer. Each employee has one
passkey; after that it works on your other devices too, because iCloud and
Google sync it. Every clock-in asks for your face or PIN again.

**A lost or new phone.** The screen that refuses you has a button to ask HR
for a reset. HR sees what your new phone looks like next to your old one, and
resets it in one click.

**Signing in with your passkey.** When the workspace turns it on (System
Settings → Login with Passkey), the login page offers *Sign in with passkey*,
and no password is needed.

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

**What runs on its own**, each with a switch in HR Settings:

| When | What | Switch |
|---|---|---|
| A new applicant | Rated and ranked | Auto Screen New Applicants |
| A new interview | Questions prepared | Auto Prepare Interviews |
| A recording ends | Transcribed and commented on | Auto Transcribe Recordings |
| A new grievance | Summarised and categorised | Auto Triage Grievances |

Each is one AI call per event and uses the workspace's AI credits. Comments
from these are written by a user called **OneAI**. Which model each uses is set
on the OneAI settings screen: **Screen applicants**, **Interviews**,
**Grievances** and **Transcribe**. Transcribe needs a model that reads audio.

## Under the hood

For the people who build OneHR. OneAI does not read past this heading.

### Where things are

| File | What it does |
|---|---|
| `employee.py`, `own.py`, `names.py`, `money.py`, `leaving.py` | The employee record's answers, who the reader is, names for IDs, currency, the last day |
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
  Status is read-only, and the record carries who, when and the note.
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
