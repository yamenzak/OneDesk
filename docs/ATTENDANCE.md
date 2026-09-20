# Attendance without a machine

Written by hand. A plan, not generated reference.

An employee presses **Clock in**. No terminal, no fingerprint reader, no app.
Three gates decide whether the press counts, a fourth check says who was holding
the phone, and everything each gate saw is written down whether it passed or
not. What is written down is what lets the system correct itself — new office
address, moved warehouse gate, replaced phone — without anybody editing a
settings box.

## The three gates

**1. The place.** The browser sends a position and the server checks it against
the fence. HRMS already enforces this: `Shift Location` has coordinates and
`checkin_radius`, `Shift Assignment` points a shift at one, and
`EmployeeCheckin.validate_distance_from_shift_location` refuses past it when
`HR Settings.allow_geolocation_tracking` is on. It has always worked. What it
never had was a screen that asked the browser for a position.

The browser asks the employee's permission once. A refusal is a flag, not a
locked door — a denied prompt on somebody's first morning is a support call.
Accuracy comes with the position and is recorded: a laptop with no GPS answers
"somewhere within two kilometres", and so does a fake, so anything vaguer than
the fence is a flag even when the coordinates land inside it.

**2. The network.** The address the request arrived from has to be one of the
office's. Read from `frappe.local.request_ip`, never from a header the caller
sets, because a header is the whole of the attack on this kind of rule. A
browser cannot read an SSID and never will, so "the office wifi" honestly means
"the address we see you arriving from".

OneApp already wrote this, in `oneapp/onehr/place.py`. The one change: the
addresses stop being a textarea and become rows, because a textarea cannot
learn and rows can.

**3. The device.** The first clock-in from a browser makes a random secret,
keeps it, and registers it as a row: this browser is Rania's. Every clock-in
after that carries it.

A device belongs to **one** employee. That rule is the whole point. One person
signing in as five colleagues on the reception PC and clocking them all in
produces five attempts naming one device, which is not a subtle pattern. Without
the rule the PC just becomes everybody's first device and the gate does nothing.

A mismatch lets the clock-in through and writes a flag, because refusing would
leave a new starter with a new phone standing outside. Clearing browser data
loses the secret, which is why it is kept in two places — a server-set cookie
and browser storage, either restoring the other — and why an installed PWA is
worth a one-line prompt, since its storage survives clearing the browser.

## The fourth check: who was holding the phone

A passkey. This is the one part that is genuinely strong, and it is worth being
exact about what it does.

A passkey is a key pair created by the phone and kept in its secure hardware or
its keychain. Registering one is a prompt; using one is Face ID, a fingerprint
or the device PIN. We ask for it with `userVerification: "required"`, which
means **every clock-in needs the owner's face or PIN**, not just the first.

What that fixes: handing your unlocked phone to a colleague stops being enough.
They need your face at the moment they press the button, every time. That is the
borrowed-phone case, which nothing else on this list touches.

Three things to be honest about:

- **A passkey does not identify a device.** All we get back is a credential id,
  and two employees registering on the same phone produce two unrelated ids with
  nothing linking them. So the device secret from gate 3 stays: the secret says
  which browser, the passkey says which person.
- **Passkeys sync.** iCloud Keychain and Google Password Manager copy them
  across that person's own devices by default. That is fine — still the same
  person — but it means "one passkey, one device" is not true. The
  authenticator tells us whether a credential is synced (`backupEligible`,
  `backupState`) and we record it.
- **Frappe has no WebAuthn in v17.** This is real work, not a switch. It is the
  one thing on this plan we build from scratch.

## Everyone who clocks themselves in has a login

This is the constraint that decides the shape of the whole thing, so it goes
before the schema.

An employee with no `User` record has no session, and with no session there is
nothing for the server to check and no permission under which to write a row.
Anybody holding the link would be them. So self-service and having an account
are the same decision, and the setup screen should say so in one sentence rather
than pretending otherwise.

A **Website User** costs nothing, carries no desk access, and is what HRMS's own
ESS and PWA already assume. Creating one is a checkbox on Employee
(`create_user_permission` already exists and already scopes them to their own
record). With a passkey they never need a password at all — the passkey *is* the
login, which is a better experience than the password they would otherwise
forget.

For people who will never have a phone or an account, the answer is a shared
tablet at the door running as itself, where the person identifies themselves
with a PIN, or a supervisor marking the roll. Both are honest; neither pretends
to be individual authentication.

## Everything is written down, passed or refused

`Employee Checkin` only records successes. The refusals are the interesting
ones, so there is a second row for every attempt.

**`Checkin Attempt`** — employee, time (the server's, always), outcome, score,
and what each gate saw: the address, the network row it matched or did not, the
position and its accuracy, the zone it landed in, the device, whether a passkey
was used and verified, the user agent, platform, model and screen. If a clock-in
was written, a link to it.

Attached to it, one row per signal that fired: the signal's name, its weight,
and a sentence a human can read.

This table is three things at once: the review queue, the evidence when somebody
disputes a day, and the data the self-healing reads. Without it the flags are
theatre and nothing can learn.

## The score, and the two things it measures

Weights on named signals, added up. No model, nothing learned in a way nobody
can explain — when a clock-in is refused, the screen has to say which three
things were wrong.

**Confidence** is per attempt: how sure are we this was the employee, here, now.

**Standing** is per employee and moves slowly: a rolling read of their last
ninety days of attempts. Standing is not used to refuse anybody. It is used to
decide **whose observations count** when the system teaches itself something
new, which is the next section. Somebody with three months of clean clock-ins
from one device is a witness. Somebody in their first week is not.

Signals worth having on day one:

- the device is unknown, or belongs to somebody else
- several employees on one device inside an hour
- one employee on several devices inside an hour
- the address has never been seen before
- the position is outside every zone, or its accuracy is vaguer than the fence
- location permission was refused
- two clock-ins too far apart for the time between them
- for employees with a `User`: their desk session is active from a different
  address than the clock-in came from, which `Activity Log` and
  `User Session Display` already record and which costs us nothing to read
- the clock-in landed in the same second as somebody else's, which is a script
- a day closed automatically because nobody clocked out

## Self-healing

The point of writing everything down. Three things learn, and all three follow
the same rule: **a change is only proposed by attempts that were already
corroborated another way.** Three colleagues in a café cannot promote the café,
because none of them was inside a fence or on a known network when they voted.

**The office address changes.** A router reboots, a mesh node hands out a
different egress, an office gets a second line for 5GHz, a site moves to 4G
backup. Today that locks everybody out on a Monday morning. Instead: an unknown
address seen from several employees who were each inside the fence, on trusted
devices, within a window, becomes a `Checkin Network` row with status
**Proposed**, and at a threshold the workspace sets, **Confirmed**. Nobody
touches a settings box. HR sees a notification saying what was learned and can
reject it.

**The fence is in the wrong place.** A warehouse registered at its office door
has its staff clocking in at the gate two hundred metres away; a site moves. The
positions of corroborated clock-ins cluster, and a cluster that sits outside
every zone but is used by enough people becomes a **Proposed** `Checkin Zone`
against that Shift Location — a second circle, not a wider one, because widening
the radius to cover a car park also covers the road.

**A phone is replaced.** When a new secret appears, compare what we recorded
against the retired device: user agent, platform, model, screen, renderer, and
the addresses it used. If they match, the flag reads *same phone, browser was
cleared* and clears itself. If they do not, it stays for HR. Either way one
re-registration is noise and four in a week is the actual signal.

Nothing auto-heals in the direction of *less* security: a proposal can widen
where people may clock in, never who may. Devices, passkeys and employees are
never promoted automatically.

## Who can do what

- **The employee** clocks themselves in, and sees their own device list.
- **HR User** approves a new device, retires an old one, and works the review
  queue. This is the day-to-day job, and the volume is a handful a month.
- **HR Manager** changes the policy, blocks a device, confirms or rejects a
  proposed network or zone, and sets the thresholds.
- **Nobody's own manager**, deliberately. Approving your own team's devices is
  the conflict this system exists to catch.

## The schema

**Four new doctypes.**

`Checkin Device` — employee, label, hashed secret, status (Active, Retired,
Blocked), first and last seen, last address, and the fingerprint: user agent,
platform, model, screen, renderer. Plus the passkey when there is one:
credential id, public key, sign count, aaguid, whether it is backed up.

`Checkin Network` — an address or range, the Shift Location it belongs to (or
none, for the whole workspace), status (Declared, Proposed, Confirmed,
Rejected), first and last seen, how many attempts and how many distinct
employees have used it.

`Checkin Zone` — a Shift Location, coordinates, radius, status with the same
four values, and the same counts. The Shift Location's own circle stays where it
is; zones are the extra ones, including the learned ones.

`Checkin Attempt` — as above, with `Checkin Signal` as its child table.

**Custom fields, on things that already exist.**

`HR Settings`: self clock-in on or off, which gates are on, whether an unknown
device refuses or only flags, whether a passkey is required, the auto-confirm
thresholds for networks and zones, whether the day auto-closes, the optional
photo and how long it is kept.

`Shift Location`: whether this place is a fence (refuse outside) or a site
(record the distance and flag), and a child table of other places this shift may
clock in from — a depot plus four live sites in one record instead of four
overlapping shift assignments.

`Employee Checkin`: a link to the attempt that produced it, and a reason on the
way out — break, lunch, errand, done for the day — which costs nothing and makes
a day of gaps readable.

**What we reuse and do not touch.** `Employee Checkin` is still written as an
ordinary document with HRMS's validation running: no `ignore_permissions`, no
second writer. `Shift Type` still computes the day — half days, late marks,
early exits, absent thresholds, all of it. `Attendance Request` is still how a
day becomes Work From Home or On Duty. `Holiday List` still says when the place
is closed. From frappe: `User` and `User Permission` for the account and its
scope, `Activity Log` and `User Session Display` for the corroboration signal,
`File` for the optional photo, `Notification` for the nudge and the learned-a-
thing message.

**`attendance_device_id` on Employee is not part of this.** It is the number a
biometric terminal knows somebody by, it arrives on `Employee Checkin.device_id`
when a box syncs its logs, and reusing it here would make one field mean two
things.

## One fix upstream

`validate_distance_from_shift_location` collects **every** Shift Location
assigned to the employee for that shift and then checks `[0]`. The list is built
and thrown away. Checking all of them and passing on any is a few lines, and it
is the difference between one fence and a set. It goes in `docs/OVERRIDES.md`
and is worth offering back to HRMS.

## The optional photo, and why it is not a gate

The idea was a photo as a carrier: snap anything, a black frame or the ceiling,
and read the EXIF for time, device and position. It does not work, and it is
written down here so nobody proposes it again.

A canvas capture has no EXIF at all. A photo that has EXIF came from a file, and
accepting a file is exactly what the camera path exists to prevent; iOS strips
location from files handed to a web page anyway, and EXIF is plain text a person
can edit. The timestamp in EXIF is the phone's clock, set by the phone's owner,
where the server already knows when the request arrived. The device comes from
the browser — camera label, model on Android Chrome, WebGL renderer, screen size
— on the same request, with no file involved.

And without a position the picture proves nothing: the same black frame
photographs identically from the car park, from home and from bed.

What a photo can still do is answer *who*, which is a different feature. A live
frame from `getUserMedia`, no file input anywhere, shown to a human in the review
queue beside the employee's own profile photo. No face recognition, no template,
nothing computed. Off by default, and mostly redundant once passkeys are in.

## What gets refused and what gets flagged

Refuse on what is certain: the network is wrong, or the position is outside
every zone of a place that is a fence, or a required passkey was not presented.

Flag on what is a guess: an unfamiliar device, a refused location prompt, poor
accuracy, impossible travel, several people on one device, a session from
somewhere else, an auto-closed day.

A month of flags is a conversation a manager can have. A month of silent
refusals is a month of people ringing HR from the car park, and it is how these
systems get switched off.

## Stages

1. **The ledger.** `Checkin Attempt` and `Checkin Signal`, written on every
   attempt, with no gate enforcing anything yet. Everything else reads this, so
   it comes first, and a week of it on a real site is worth more than any
   amount of guessing at thresholds.
2. **The device.** `Checkin Device`, register on first use, one owner per
   device, flag on mismatch, cookie and storage, the PWA prompt.
3. **The network.** `Checkin Network` as rows, one click to learn the office
   address, the refusal that reads it.
4. **The place.** Ask the browser for a position, record accuracy, `Checkin
   Zone`, and make HRMS's fence reachable for the first time. Plus the upstream
   fix and the fence-or-site switch.
5. **The review queue.** One screen listing the flags with everything each
   attempt saw. Without this the first four stages are data nobody reads.
6. **The score.** Weights, confidence per attempt, standing per employee, and
   the sentence that explains a refusal.
7. **Self-healing.** Proposed networks and zones, the thresholds, the
   notification, the device-replacement match.
8. **Passkeys.** Registration, `userVerification: "required"`, and passwordless
   login for employees who only ever clock in.
9. **Closing the day.** Auto-close at shift end, one nudge, the reason on the
   way out, and the auto-closed log marked as such rather than looking real.
10. **The optional photo**, if anybody still wants it.

## What we are not building

- **Face recognition.** Liability, bias and a procurement conversation, to
  answer a question the passkey answers better.
- **A native app.** All of this is a browser.
- **Our own shift maths.** HRMS's is correct and already runs on a schedule.
- **An SSID check.** There is no web API for it and there should not be.
- **Anything that trusts the client's clock.**
- **Random presence pings.** They measure presence at a screen, everybody knows
  it, and the first thing they produce is a culture that games them.
- **A photo read for its metadata.** See above.
- **A score nobody can explain.** If a refusal cannot be put in a sentence, the
  signal that caused it does not ship.

## What this is honestly worth

Three gates and a passkey make it very likely that the employee's own device, at
the office, on the office network, with their face or PIN, pressed the button.
That is a long way past what a spreadsheet or an honour system gives, and past
most badge systems, where people prop the door and badge a friend in.

It is not proof that a body is in a building. No browser can give that, and no
native app can either. The goal is that cheating is annoying, repeated cheating
is visible in the ledger, and the system does not punish honest people for a
router reboot.
