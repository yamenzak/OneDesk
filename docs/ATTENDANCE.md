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
already ships and which already does exactly this: pick a date, a shift, a
department, tick the people. We add nothing to it. It is the honest answer for
the warehouse with no phones and for the person whose device is too old, and
attendance marked that way is plainly attendance somebody asserted rather than
attendance the system observed.

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
  see everyone's through the `Checkin Device` list.
- **The library.** `py_webauthn` (BSD-3, on PyPI as `webauthn`) does the
  registration and assertion verification. We add the dependency rather than
  writing CBOR parsing and COSE key handling ourselves, which is
  security-critical code with no reason to be ours. `cryptography` is already in
  the bench.

## Remote and home working

The gates do not change shape; what they point at does.

**The network becomes personal.** A home has a public address that is stable for
weeks at a time, so the same `Checkin Network` machinery learns it — a row
scoped to an employee rather than to a place. First clock-in from home proposes
it, and after that home is as good a network as the office. When the ISP changes
it, the same self-healing that handles a router reboot at the office handles it
here.

**The fence becomes their address**, if they want one. A `Checkin Zone` scoped
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

**`Checkin Attempt`** — employee, the server's time, outcome, score, and what
each gate saw: the credential and whether user verification happened, the
address and the network row it matched, the position with its accuracy and the
zone it landed in, the user agent, platform, model, screen and renderer. A link
to the `Employee Checkin` when one was written, and to the photo when there is
one.

Under it, one `Checkin Signal` row per signal that fired: name, weight, and a
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
within a window, becomes a `Checkin Network` row marked **Proposed**, and at the
workspace's threshold **Confirmed**. HR gets one notification saying what was
learned and can reject it.

**The fence is in the wrong place.** A warehouse registered at its office door
has its staff clocking in at the gate; a site moves. Corroborated positions
cluster, and a cluster outside every zone used by enough people becomes a
**Proposed** `Checkin Zone` against that Shift Location — a second circle, not a
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

## The schema

**Four new doctypes.**

`Checkin Device` — the passkey. Employee, credential id, public key, sign count,
aaguid, whether it is backed up, status (Active, Reset, Blocked), registered and
last used, last address, and what the browser looked like at registration: user
agent, platform, model, screen, renderer. The fingerprint is not the identity;
it is what makes a reset request recognisable and what shows several employees
enrolling from one machine.

`Checkin Network` — an address or range; the Shift Location it belongs to, or
the employee it belongs to for a home worker, or neither for the whole
workspace; status (Declared, Proposed, Confirmed, Rejected); first and last
seen; how many attempts and how many distinct employees have used it.

`Checkin Zone` — a Shift Location or an employee, coordinates, radius, the same
four statuses and the same counts. A Shift Location's own circle stays where it
is; zones are the extra ones, including the learned ones.

`Checkin Attempt` — as above, with `Checkin Signal` as its child table.

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

`Employee Checkin` — a link to the attempt that produced it, and the reason on
the way out.

`System Settings` — login with passkey, beside the two login-method switches
already in that section.

`User` — the passkey section described above.

**One dependency.** `webauthn` (py_webauthn, BSD-3) in `pyproject.toml`.

**`attendance_device_id` on Employee is not part of this.** It is the number a
biometric terminal knows somebody by, it arrives on `Employee Checkin.device_id`
when a box syncs its logs, and reusing it here would make one field mean two
things.

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

1. **The ledger.** `Checkin Attempt` and `Checkin Signal`, written on every
   attempt, enforcing nothing. Everything else reads this, and a week of real
   attempts is worth more than any amount of guessing at thresholds.
2. **The passkey.** `Checkin Device`, the `webauthn` dependency, registration
   refused from a desktop, one credential per employee,
   `userVerification: "required"`, and the reset HR does in one click.
3. **The network.** `Checkin Network` as rows, one click to learn the office
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
