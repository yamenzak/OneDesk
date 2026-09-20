# Attendance without a machine

Written by hand. A plan, not generated reference.

An employee presses **Clock in**. No terminal, no fingerprint reader, no app.
Three gates decide whether the press counts — the place, the network, and a
passkey on their own phone — and everything each gate saw is written down
whether it passed or not. What is written down is what lets the system correct
itself: a new office address, a warehouse gate two hundred metres from the door,
a replaced phone, all without anybody editing a settings box.

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

**3. The device, which is the passkey.** A passkey is a key pair the phone
creates and keeps in its secure hardware or its keychain. Registering one is a
prompt; using one is Face ID, a fingerprint or the device PIN, and we ask with
`userVerification: "required"` so that happens on **every** clock-in, not just
the first.

Every assertion hands back the credential id, and that id is the device
identity. It is stable, it is cryptographic, and unlike a cookie it cannot be
cleared, copied, or stepped around by opening a private window — it lives in the
operating system's keychain, not in the browser profile.

**One credential per employee.** A second registration is refused and needs HR
to reset the first. That rule is what makes the gate work: a colleague who knows
your password and signs in as you on their own phone finds there is no passkey
there and cannot make one, so they cannot clock in as you. The only way through
is your actual phone, in their hand, with your face or PIN — which is a
different and much larger favour to ask, and not one anybody does.

Four things to be exact about.

**Registration has to happen on a phone.** If somebody enrols their passkey on
the office PC through Windows Hello, the whole argument collapses — the device
is then a shared machine anybody can stand in front of. So registration is
refused from a desktop browser and the enrolment screen says to use your phone.

**Passkeys sync.** iCloud Keychain and Google Password Manager copy them across
that person's own devices, so the same credential id can appear from their
tablet. It is still them, and the other two gates still apply. The authenticator
says whether a credential is backed up and we record it.

**There is no cookie and no device secret.** An earlier draft had one. It is
redundant once the passkey is the identity, and it was weak on its own: a
private window sends no cookie and reads no storage, so anybody avoiding the
check just opened one. What replaces it for spotting patterns costs nothing —
the user agent, platform, model, screen and renderer arrive on every request
anyway and go in the ledger, so five different employees authenticating from
what is obviously one machine is visible there without a cookie.

**Losing the phone is HR's one click.** Somebody with a new or broken phone
cannot clock in until the credential is reset, which is the point, so the screen
that refuses them has the button that asks for the reset and HR sees it
immediately. A workspace that cannot answer that within a morning should run the
gate as a flag rather than a refusal.

**When there is no passkey at all** — a device too old for WebAuthn, or a
workspace that has not turned the gate on — the other two gates and the ledger
carry it. Those people are the kiosk-and-supervisor case below.

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

- no passkey was presented, where one is required
- several employees authenticating from what looks like one machine
- a passkey used from a browser that looks nothing like the one it was
  registered on
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

**A phone is replaced.** A reset request carries what the new browser looks like
and what the old one did, so HR sees *same model, same network, new phone* or
*different everything* rather than a bare "please reset". It is one click either
way, and a second reset within a month is the thing worth looking at.

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

`Checkin Device` — the passkey, one row per employee: credential id, public key,
sign count, aaguid, whether it is backed up, status (Active, Reset, Blocked),
first and last seen, last address, and what the browser looked like at
registration — user agent, platform, model, screen, renderer. The fingerprint is
not the identity; it is what makes a reset request recognisable and what shows
several employees enrolling from one machine.

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
2. **The passkey.** WebAuthn registration and assertion, one credential per
   employee, `userVerification: "required"`, registration refused from a
   desktop, and the reset that HR does in one click. It is the device gate, so
   it comes before the other two rather than last.
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
8. **Passwordless login.** The same credential signs people in, so an employee
   who only ever clocks in never has a password to forget.
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
