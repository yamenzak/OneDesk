# Attendance without a machine

Written by hand. A plan, and now also a description: every stage below is
built. What changed while building it is noted where it happened.

An employee presses **Clock in**. No terminal, no fingerprint reader, no app, no
hardware of any kind. Who they are is a passkey on their own phone. Where they
are is the network they arrived on and the position their browser reports. Every
attempt is written down whether it passed or not, and that record is what lets
the system fix its own settings — a new office address, a warehouse gate two
hundred metres from the door, a replaced phone — without anybody editing a
settings box.

## The gates, in order

**Gate 1 — the passkey.** Who. A hard refusal: no passkey, no clock-in.

**Gate 2 — the network.** The address the request arrived from, against the
places this employee may clock in from. One string comparison, no permission
prompt, instant.

**Gate 3 — the place.** The position the browser reports, against the fence.
Needs the employee's permission and a second or two for a fix, so it runs after
the two cheap ones and only when they passed.

**Gate 4 — the photo.** Optional, off by default, only where a workspace turns
it on or the score is already low.

The order is about cost, not importance: never ask for GPS from somebody whose
passkey already failed.

**Gates 2 and 3 are judged together, and the policy says how.** *Either* is the
sensible default — the office wifi or inside the fence proves the same thing two
ways, and demanding both means one flaky GPS fix stops somebody working. *Both*
is there for workspaces that mean it. Gate 1 is never optional once it is on.

## Who this works for, and who is marked by hand

**Every employee with a `User` and a phone made in the last six years**, whether
they are a Website User who only ever clocks in or a full desk user in
accounting. Same gates, same screens.

**Everybody else is marked by HR**, using `Employee Attendance Tool`, which HRMS
already ships and which already does most of this: pick a date, a shift, a
department, tick the people. It is the honest answer for the warehouse with no
phones and for the person whose device is too old, and attendance marked that
way is plainly attendance somebody asserted rather than attendance the system
observed.

The screen is rearranged into the three steps it actually is — the day, then
who, then what to mark them as — because hrms interleaves them, and the
checkboxes that qualify the status sat a screen above it while the six filters
nobody sets were the first thing on the page. **Tick Everyone Who Checked In**
reads the ledger for the date and ticks whoever has an IN log, so a day that
is half clocked and half asserted is not retyped; a log a reviewer rejected
carries `skip_auto_attendance` and is left out. A **Search** box hides the rows
that do not match, without touching the ticks, because a department of sixty is
three columns of checkboxes with no way through it. And the heading reads
**Mark Attendance**, which is what the rail calls it; a DocType has no label to
set, so the last breadcrumb is replaced instead.

## Overtime

Overtime lives on the Attendance row — `overtime_type`,
`actual_overtime_duration` and `standard_working_hours` — and there is one
place to record it, because a shift writing it from the check-ins and a person
writing it by hand are two hands on the same three fields. `Overtime Slip`
collects submitted days marked Present with an Overtime Type and turns them
into an `Additional Salary`, without knowing which hand wrote them.

The hand is `one_hr/overtime.py` and a dialog, offered from the Employee record
and from the Attendance itself. It is a dialog rather than a column in the bulk
tool because overtime is one person's extra hours on one date; a whole
department rarely works the same two hours. The dialog asks the server what the
day is before it offers to write anything, so it says "no attendance marked on
21-09-2026" rather than failing on submit, and it shows the standard day — the
shift's own length, or `HR Settings.standard_working_hours`, which
`one_hr/policy.py` starts at eight because zero makes every hour of a shiftless
day overtime.

The fields are read only on the form and the row is submitted by the time
anybody notices the overtime, so `record` writes them straight to the row and
leaves a comment naming who did it. Nothing is posted at Attendance submit, so
there is no ledger to disagree with.

`Overtime Slip` also lets a row be typed with no Attendance behind it, which is
the one way to be paid twice for one day. `no_double_pay` refuses a hand-typed
row whose date already carries overtime on the Attendance, and names the row to
remove.

Self-service and having an account are the same decision. An employee with no
`User` has no session, and with no session there is nothing for the server to
check and no permission under which to write a row. A Website User costs
nothing, carries no desk access, and is what HRMS's ESS already assumes.

## The passkey

A key pair the phone creates and keeps in its secure hardware or keychain.
Registering one is a prompt. Using one is Face ID, a fingerprint or the device
PIN, and we ask with `userVerification: "required"` so that happens on **every**
clock-in, not only the first.

Every assertion hands back the credential id, and that id is the device
identity. It is stable, it is cryptographic, and unlike a cookie it cannot be
cleared, copied, or stepped around by opening a private window, because it lives
in the operating system's keychain and not in the browser profile.

**One credential per employee.** A second registration is refused and needs HR
to reset the first. That rule is the gate: a colleague who knows your password
and signs in as you on their own phone finds no passkey there and cannot make
one. The only way through is your actual phone with your face or PIN, which is a
different and much larger favour to ask.

**Registration has to happen on a phone.** A passkey enrolled on the office PC
through Windows Hello turns the device back into a shared machine and the whole
argument collapses. Registration is refused from a desktop browser and the
enrolment screen says to use your phone.

**Afterwards, any device works** — and this is a feature rather than a hole.
Passkeys sync through iCloud Keychain and Google Password Manager, so the same
credential appears on that person's laptop and tablet. It is still them, it
still needs their face or PIN, and gates 2 and 3 still have to pass. Somebody
who clocks in from their work laptop at their desk is fine. The authenticator
tells us whether a credential is backed up and we record it.

**There is no cookie and no device secret.** An earlier draft had one. It is
redundant once the passkey is the identity, and it was weak on its own, because
a private window sends no cookie and reads no storage. The pattern-spotting it
was doing costs nothing to keep: user agent, platform, model, screen and
renderer arrive on every request anyway and go in the ledger, so several
employees authenticating from obviously one machine is still visible.

**Losing a phone is one click for HR.** The screen that refuses carries the
button that asks for a reset, the request shows what the new browser looks like
beside what the old one did, and HR sees it immediately. A workspace that cannot
answer within a morning should run the gate as a flag rather than a refusal.

### The passkey is also how you sign in

Once an employee has one, it can carry the login too, and for somebody who only
ever clocks in that means no password to forget and none to lend out.

- **The login page.** `web_include_js` reaches it — `templates/base.html`
  renders those includes and `login.html` extends it — so One adds a *Sign in
  with passkey* button to the card without replacing frappe's template. A
  discoverable credential means the browser offers the account; nothing is
  typed.
- **The switch.** `System Settings` already has a `login_methods_section`
  holding `disable_user_pass_login` and `login_with_email_link`. Ours is a
  custom field beside them.
- **Managing them.** A section on `User` listing that person's credential, when
  it was registered and last used, with a button to remove it. Administrators
  see everyone's through the `Clock Device` list.
- **The library.** `py_webauthn` (BSD-3, on PyPI as `webauthn`) does the
  registration and assertion verification. We add the dependency rather than
  writing CBOR parsing and COSE key handling ourselves, which is
  security-critical code with no reason to be ours. `cryptography` is already in
  the bench.

## Remote and home working

The gates do not change shape; what they point at does.

**The network becomes personal.** A home has a public address that is stable for
weeks at a time, so the same `Clock Network` machinery learns it — a row
scoped to an employee rather than to a place. First clock-in from home proposes
it, and after that home is as good a network as the office. When the ISP changes
it, the same self-healing that handles a router reboot at the office handles it
here.

**The fence becomes their address**, if they want one. A `Clock Place` scoped
to the employee, set from their own position on the first day, with a radius
loose enough that a home address is not published to the company by accident.
Opt-in per workspace, because plenty of places do not want to hold it.

**Frappe already knows when a desk worker started.** Most remote employees are
system users — accounts, IT, the project team — and `Activity Log` records their
login with its address, while `User Session Display` holds the live session. A
clock-in that matches an active session from the same address is corroborated
for free; a clock-in while their only session is live from another country is a
signal worth having. It is a signal, never a clock: we do not mark somebody
present because they opened a page.

**Several clock-ins a day are already supported and are not required.**
`Shift Type.working_hours_calculation_based_on` can sum every valid IN/OUT pair
rather than the first and last, so a lunch break is an OUT and an IN and the
hours come out right. Whether a workplace asks for that is a sentence in their
policy. What we add is the reason on the way out — break, lunch, errand, done
for the day — which costs nothing and makes a day of gaps readable.

**What the photo does and does not do for a remote worker.** It is not a
substitute for the office network and it cannot be: there is no location in it.
A canvas capture carries no EXIF at all, a file that carries EXIF is a file
somebody chose and EXIF is plain text they can edit, and iOS strips location
from photos handed to a web page anyway. So the camera opens inside the page
with `getUserMedia`, there is no file input anywhere, and the position still
comes from gate 3 at the same instant. What the photo is worth is that a person
looks at it: a deterrent, and evidence when something is disputed. A workspace
can switch it on for everybody, for home workers only, or for attempts the score
has already doubted.

## Everything is written down, passed or refused

`Employee Checkin` only records successes, and the refusals are the interesting
ones, so every attempt writes its own row.

**`Clock Attempt`** — employee, the server's time, outcome, score, and what
each gate saw: the credential and whether user verification happened, the
address and the network row it matched, the position with its accuracy and the
zone it landed in, the user agent, platform, model, screen and renderer. A link
to the `Employee Checkin` when one was written, and to the photo when there is
one.

Under it, one `Clock Signal` row per signal that fired: name, weight, and a
sentence a person can read.

This table is the review queue, the evidence when somebody disputes a day, and
the data the self-healing reads. Without it the flags are theatre and nothing
can learn.

## The score

Named signals with weights, added up. No model. When a clock-in is refused the
screen has to say which three things were wrong, so a signal that cannot be put
in a sentence does not ship.

**Confidence** is per attempt: how sure we are that this was the employee, here,
now. It decides allow, flag or refuse.

**Standing** is per employee, moves slowly, and lives on the Employee record as
a read-only field recomputed nightly from the last ninety days. It never refuses
anybody by itself. It decides **whose observations count** when the system
teaches itself something new: three clean months makes somebody a witness, a
first week does not.

Signals worth having on day one:

- no passkey where one is required, or user verification did not happen
- several employees authenticating from what is obviously one machine
- a credential used from a browser nothing like the one it registered on
- an address never seen before, by anyone or by this employee
- a position outside every zone, or an accuracy vaguer than the fence
- location permission refused
- two clock-ins further apart than the time between them allows
- a desk session live from a different address than the clock-in came from
- clock-ins landing in the same second, which is a script
- a day closed automatically because nobody clocked out
- a second passkey reset within a month

## Self-healing

The point of writing everything down. Three things learn, under one rule:
**only attempts that were already corroborated another way may propose a
change.** Three colleagues in a café cannot promote the café, because none of
them was inside a fence or on a known network when they voted.

**The office address changes.** A router reboots, a mesh node hands out a
different egress, a second line appears for the 5GHz band, a site falls back to
4G. Today that locks everybody out on a Monday. Instead, an unknown address seen
from several employees who were each inside the fence, each with standing,
within a window, becomes a `Clock Network` row marked **Proposed**, and at the
workspace's threshold **Confirmed**. HR gets one notification saying what was
learned and can reject it.

**The fence is in the wrong place.** A warehouse registered at its office door
has its staff clocking in at the gate; a site moves. Corroborated positions
cluster, and a cluster outside every zone used by enough people becomes a
**Proposed** `Clock Place` against that Shift Location — a second circle, not a
wider one, because widening the radius to cover a car park also covers the road.

**A phone is replaced.** The reset request carries what the new browser looks
like beside what the old one did, so HR reads *same model, same network, new
phone* or *different everything* rather than a bare "please reset". One click
either way, and a second reset inside a month is the thing to look at.

Nothing heals towards less security. A proposal can widen *where* people may
clock in, never *who* may. Credentials, employees and standing are never
promoted automatically.

## The control in the rail

Clocking in should not be a place you navigate to. `frappe.ui.Dock` exposes
`get_shortcuts()` — an array of items with `icon`, `label`, `badge`, `condition`
and `on_click` — and One already subclasses `Dock`, so the control is one more
shortcut returned alongside frappe's search and notifications.

It shows the state rather than a button: a dot that is green while clocked in
and grey while not, the hours so far on hover, and a click that clocks in or out
the right way round — the direction is read from where the person already is,
never sent by a browser tab that has been open since this morning. Somebody
who is on leave or on a holiday is not offered a direction at all.

`condition` hides it from anyone with no Employee record, and from a workspace
with self clock-in off.

## Who can do what

- **The employee** clocks in and out, sees their own credential and their own
  attempts.
- **HR User** resets a credential, works the review queue, and marks attendance
  by hand with `Employee Attendance Tool`. A handful of actions a month.
- **HR Manager** sets the policy, blocks a credential, confirms or rejects a
  proposed network or zone, and sets the thresholds.
- **Never somebody's own manager.** Approving your own team's devices is the
  conflict this system exists to catch.

## Before any of it works

hrms turns `Employee Checkin` pairs into `Attendance` from one scheduled job,
and `ShiftType.has_incorrect_shift_config` makes that job return **without a
word** unless the shift has auto attendance on, a date to process after and a
last sync. A workspace missing one takes check-ins all week and has an empty
Attendance list, empty charts, an empty Overtime Slip and no error anywhere.
`auto_update_last_sync` is the fourth: without it the sync stays where it was
set and processing quietly stops past that moment.

So the four are set three ways. The **setup wizard** asks when people work —
start, end and the week's day off — and out of that one answer writes this
year's `Holiday List` (the weekly off plus the country's public holidays,
through erpnext's own `get_local_holidays`), sets it as the company's default,
sets `HR Settings.standard_working_hours` to the length of the day, and creates
the `Day` shift with all four. The **Shift Type form** says so in a headline and
offers one button, `Read Check-ins`, where the fix is. And
`one_hr/setup.nightly` checks the shifts that actually have check-ins and tells
every HR Manager once a week about any that are deaf.

The wizard asks because the alternative is a clock that takes check-ins from
the first morning and produces nothing until somebody is told why.

## Where the settings are

The rail's **Attendance Settings** opens `HR Settings`, which is seven tabs
covering leave, expenses, tenure and recruitment as well. It used to land on
the Employee tab — naming series, retirement age, birthday reminders — two tabs
from anything it named. A `field_order` property setter puts the attendance tab
first, so the row tells the truth and the rest is one click away; the whole of
HR Settings has its own entry in the Setup workspace.

Two things moved onto that tab. **Standard Working Hours** decides what counts
as overtime and sat beside Retirement Age with no unit and no description.
**Allow Geolocation Tracking** is hrms's, and `one_hr/checkin.py` reads it: with
it off nothing records where a check-in came from and the location gate cannot
run, so it belongs with the gate it governs. What is left of hrms's own tab is
one shift setting, so it is labelled **Shift**.

**Five tabs, not seven.** Shift was one checkbox on a tab of its own and
Tenure was two fields about the exit questionnaire. The shift setting joins
Attendance — which is what hrms called the two together before it split them —
and the exit questionnaire joins Employee, under Leaving, beside naming and
retirement age. Both tab breaks are hidden rather than removed, because they
are hrms's fields and a later version may put something else on them.

**Allow Employee Checkin from Mobile App is hidden.** It is read only by
hrms's own mobile API; ours is governed by Allow Employees to Check In
Themselves, two fields above. Two switches that look like the same switch, one
of which does nothing here.

## The schema

**Four new doctypes.**

`Clock Device` — the passkey. Employee, credential id, public key, sign count,
aaguid, whether it is backed up, status (Active, Reset, Blocked), registered and
last used, last address, and what the browser looked like at registration: user
agent, platform, model, screen, renderer. The fingerprint is not the identity;
it is what makes a reset request recognisable and what shows several employees
enrolling from one machine. Named `DEV-YYYY-MM-#####`.

**Status is the only decision on that record, and it is not a dropdown.** It is
read only, and the form offers Reset and Block, which go through
`passkey.reset` and `passkey.retire` — the same functions the Employee record
and offboarding use — rather than letting somebody set a blocked passkey back
to Active and save.

**A block now blocks.** `held_by` asks for an *Active* credential, so a blocked
employee simply registered a new passkey and carried on; `start_registration`
checks `is_blocked` as well. A block is lifted by a reset and by nothing else,
which is why `reset` retires a blocked credential as well as an active one, and
why the form offers Reset on anything that is not already Reset.

The credential id and public key are the two fields nobody can act on, so they
sit in a collapsed Credential section under the ones that mean something: sign
count, authenticator, backed up.

`Clock Network` — an address or range; the Shift Location it belongs to, or
the employee it belongs to for a home worker, or neither for the whole
workspace; status (Declared, Proposed, Confirmed, Rejected); first and last
seen; how many attempts and how many distinct employees have used it. Named
`NET-YYYY-MM-#####`.

**Status is read only here too**, and the two decisions are buttons: Confirm on
a Proposed address, Reject on a Proposed or Confirmed one. They live in
`one_hr/learned.py` rather than on the doctype because `Clock Place` is the
same shape with the same four statuses and the same learner, and each write
leaves a comment on the record. Rejecting is final in the sense that matters:
`healing._learn` matches a Rejected row and never promotes it again.

The Seen section — first seen, last seen, attempts, employees — is what the
learner wrote, and only the learner writes it. On an address somebody typed in
it was four empty fields leaving a hole where the left column should be, so it
hides unless there is something to show. Both Belongs To fields are on screen,
because the section's own sentence offers two, and the controller refuses both
at once. The record also links to the Clock Attempts from that address, which
is what you open a proposal to look at.

`Clock Place` — a Shift Location or an employee, coordinates, radius, the same
four statuses and the same counts. Named `PLC-YYYY-MM-#####`, with the same
read-only status, the same Confirm and Reject buttons out of `learned.py`, the
same Seen section that hides when the learner wrote nothing, and the same two
Belongs To fields on screen.

**A place is a circle on the earth, and two Floats do not say whether it covers
the car park or the road.** A read-only Geolocation field draws it, on a row of
its own, redrawn from latitude, longitude and radius whenever one of them
changes — a reading of the three rather than a second place the fence is
defined. It is written onto the document rather than through `set_value`, so
opening a record does not mark it unsaved, and the map is told to remeasure
after its row has a width, because leaflet measures its container once and
would otherwise paint the circle a pixel wide.

**Use My Location had no handler at all** and did nothing. It asks the browser,
reports how accurate the answer was, and on a place that already has a centre
asks first — pressing it at a desk otherwise moves the fence to the desk.

A Shift Location's own circle stays where it is; zones are the extra ones,
including the learned ones.

`Clock Attempt` — as above, with `Clock Signal` as its child table.

`Clock Reason` — what an employee picks on the way out, with a description and
two switches. **Both switches now do something.** `Enabled` decides what the
check-out prompt offers, and the description is shown under the field as soon
as a reason is chosen, which is why a workspace writes one. `Ends the Shift`
chooses the reason a day closed at the shift end is filed under: `closing.py`
used to write the string `"Done for the day"`, and that row can be renamed or
deleted by any HR Manager, which would have left every closed day pointing at
a row that is not there. No reason carries the flag means no reason is set;
`one_auto_closed` is the part that matters and it is written either way.

Frappe hides an autoname field once a record is saved, because the title
already says it, so the Reason field is not on its own form and Description
leads.

**Custom fields on what already exists.**

`HR Settings` — self clock-in on or off; which gates are on; whether gates 2 and
3 are *either* or *both*; whether a missing passkey refuses or flags; the
auto-confirm thresholds for networks and zones; whether the day auto-closes; the
photo policy and how long a photo is kept; whether home networks and home zones
may be learned at all.

`Shift Location` — fence or site (a site records the distance and flags rather
than refusing), and a child table of other places this shift may clock in from,
so a depot plus four live sites is one record instead of four overlapping shift
assignments.

`Employee` — attendance standing, read-only, and when it was last computed.

`Employee Checkin` — a link to the attempt that produced it, the attempt's
outcome and score fetched onto the row so a list can read them without a join,
and the reason on the way out.

`System Settings` — login with passkey, beside the two login-method switches
already in that section.

`User` — the passkey section described above.

**One dependency.** `webauthn` (py_webauthn, BSD-3) in `pyproject.toml`.

**`attendance_device_id` on Employee is not part of this.** It is the number a
biometric terminal knows somebody by, it arrives on `Employee Checkin.device_id`
when a box syncs its logs, and reusing it here would make one field mean two
things. Both are hidden until a site runs a terminal.

## Reading the log list

The one question asked of `Employee Checkin` is whether a log counted, and the
Status column answered it with a blank, because hrms leaves the indicator alone
on a doctype that is not submittable. `public/js/checkin_list.js` fills it from
what the row already carries: **Rejected** when a reviewer set
`skip_auto_attendance`, **Counted** when `attendance` is set, **Flagged** when
the attempt was, and **Not counted yet** otherwise — the shift processes the
day on its own schedule, so a log written minutes ago is waiting rather than
wrong.

Two things on the form were doing harm rather than nothing. **Fetch
Geolocation** re-reads the *browser's* position and writes it over where the
person actually was, so it is offered on a new log only. **Location / Device
ID** is the biometric-terminal field above, hidden with it. And `Clock Attempt`
is named `CLK-YYYY-MM-#####` rather than a hash, because the name is what the
link field on the check-in shows. The naming is written as an expression
(`CLK-.YYYY.-.MM.-.#####`) rather than `format:`: `format:` parses each braced
part on its own, so `{#####}` asks for a counter under the empty key, which
every other `format:`-named doctype shares and which restarts at one.

## The queue

`clock_attempt_list.js` opens the list on what is waiting rather than on
everything ever recorded: `outcome = Flagged` and no verdict. The second half
was written `verdict in [""]`, which is dropped on the way to the list, so
every attempt somebody had already accepted or rejected stayed in the queue.
`verdict is not set` survives, and covers both the empty string a review leaves
and the null an untouched row has.

The columns are Employee Name, the verdict or outcome, Log Type and Score.
Employee was there twice — once as the row's title and once as its id.

**Nothing on the record may be edited**, and the framework draws a selection
box and an open-row pencil on every grid row anyway; `editable_grid: 0` stops
the typing, not the furniture, so `one-static-grid` in `desk.css` hides it. The
Check column holding the signal id (`network-unknown`) is off the grid too: the
sentence beside it already says what happened, and the id is one row-open away.

**A section with nothing in it says something false.** The Passkey section on
an attempt where no passkey was presented was one unticked box, and the
Location section on an attempt with no position was four zeros that read like
a place. Both hide on what they are about — `doc.device`, `doc.position_state`
— and Location leads with Position, which is the answer, rather than with
coordinates that may not exist.

## What we reuse and do not touch

`Employee Checkin` is still written as an ordinary document with HRMS's
validation running — no `ignore_permissions`, no second writer. `Shift Type`
still computes the day: half days, late marks, early exits, absent thresholds,
all of it. `Attendance Request` is still how a day becomes Work From Home or On
Duty. `Holiday List` still says when the place is closed. `Employee Attendance
Tool` is still how HR marks somebody by hand. From frappe: `User` and
`User Permission` for the account and its scope, `Activity Log` and
`User Session Display` for corroboration, `File` for the optional photo,
`Notification` for the nudge and the learned-a-thing message.

**One fix upstream.** `validate_distance_from_shift_location` collects every
Shift Location assigned to the employee for that shift and then checks `[0]` —
the list is built and thrown away. Checking all of them and passing on any is a
few lines, it is the difference between one fence and a set, it goes in
`docs/OVERRIDES.md`, and it is worth offering back to HRMS.

## Stages, all built

1. **The ledger.** `Clock Attempt` and `Clock Signal`, written on every
   attempt, enforcing nothing. Everything else reads this, and a week of real
   attempts is worth more than any amount of guessing at thresholds.
2. **The passkey.** `Clock Device`, the `webauthn` dependency, registration
   refused from a desktop, one credential per employee,
   `userVerification: "required"`, and the reset HR does in one click.
3. **The network.** `Clock Network` as rows, one click to learn the office
   address, the refusal that reads it, and personal rows for home workers.
4. **The place.** Ask the browser for a position, record accuracy, `Checkin
   Zone`, the upstream fix, and the fence-or-site switch.
5. **The rail control.** The shortcut, its state, and the direction read rather
   than sent.
6. **The review queue.** One screen of flagged attempts with everything each one
   saw. Without it the first four stages are data nobody reads.
7. **The score.** Weights, confidence per attempt, standing on Employee, and the
   sentence that explains a refusal.
8. **Self-healing.** Proposed networks and zones, the thresholds, the
   notification, the reset-request comparison.
9. **Passwordless login.** The same credential signs people in: the button on
   the login page, the switch in System Settings, the section on User.
10. **Closing the day.** Auto-close at shift end, one nudge, the reason on the
    way out, and the auto-closed log marked as such rather than looking real.
11. **The photo**, for workspaces that want it.

## What we are not building

- **Face recognition.** Liability, bias and a procurement conversation, to
  answer a question the passkey answers better.
- **A native app.** All of this is a browser.
- **Our own shift maths.** HRMS's is correct and already runs on a schedule.
- **An SSID check.** There is no web API for it and there should not be.
- **Anything that trusts the client's clock.**
- **Random presence pings.** They measure presence at a screen, everybody knows
  it, and the first thing they produce is a culture that games them.
- **A photo read for its metadata.** The time, the device and the position are
  all known better without it, and without the position a picture proves
  nothing: the same black frame photographs identically from the car park, from
  home and from bed.
- **A score nobody can explain.**

## Two things the building changed

**Two weights.** The wrong network and outside every fence started at thirty and
thirty-five, which flagged rather than refused. They are the two things that are
certain rather than probable, so they now cost sixty and refuse on their own.
Everything probabilistic still sits under the flag band and needs company to get
past it.

**A message that was not ours.** Every clock-in after the first put a Duplicate
Name dialog in front of somebody who had just successfully clocked in: HRMS's
telemetry claims a milestone row on each check-in and swallows the duplicate in
a savepoint, but the message survives the savepoint. `clock._write` now discards
whatever the `after_insert` hooks left in the message log, on the rule that
anything said after a document was accepted is by definition not about whether
it was accepted.

## What this is honestly worth

A passkey that needs the owner's face or PIN, on a phone nobody lends out,
arriving on the office network from inside the fence, with every attempt written
down and a system that notices patterns. That is past what a badge reader gives,
where people prop the door and badge a friend in, and far past a spreadsheet.

It is not proof that a body is in a building. No browser can give that and no
native app can either. The goal is that cheating is annoying, repeated cheating
is visible, and nobody honest is punished for a router reboot.
