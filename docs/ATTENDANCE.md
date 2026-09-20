# Attendance without a machine

A button, and what makes pressing it mean something.

No terminal, no fingerprint reader, no third-party SDK. The premise is that a
phone and a browser are enough, and that the difference between a toy and a
system is not one clever trick but a stack of cheap layers, each answering a
different lie, each switchable, and each honest about what it cannot do.

This is the plan. `docs/OVERRIDES.md` records what we lean on; the module's own
`README.md` will carry what shipped.

## What already exists, and is therefore not ours to write

Most of this is already on the bench. Building it again is the expensive
mistake, so it is listed first.

**HRMS ships the geofence.** `Shift Location` carries a position and a
`checkin_radius`; a `Shift Assignment` points an employee's shift at one;
`EmployeeCheckin.validate_distance_from_shift_location` raises
`CheckinRadiusExceededError` past it — gated on
`HR Settings.allow_geolocation_tracking`. It works. What it never had was a
browser sending a position, which is a UI problem and not a policy one.

**HRMS ships the day's arithmetic.** `Shift Type` computes the day from the
check-in pairs: `working_hours_threshold_for_half_day`,
`working_hours_threshold_for_absent`, `late_entry_grace_period`,
`early_exit_grace_period`, `working_hours_calculation_based_on`, and
`enable_auto_attendance` runs it on a schedule. Half days, late marks and early
exits are theirs. We do not compute a single one of them.

**HRMS ships the exceptions.** `Attendance Request` already means "I was working,
just not here": `reason` is *Work From Home* or *On Duty*, it takes a date range
and a half-day flag, and it writes Attendance when approved.

**HRMS ships two switches we should be reading rather than inventing.**
`HR Settings.allow_employee_checkin_from_mobile_app` and
`allow_geolocation_tracking`.

**OneApp already wrote the network rule**, in `oneapp/onehr/place.py`, and the
argument in that docstring still holds: a browser cannot read an SSID and never
will, so "the office wifi" is implemented honestly as "the address we see you
arriving from", read from `frappe.local.request_ip` and never from a header the
caller sets. It is a Custom Field of IP ranges on `Shift Location`, one per
line, because a place and the network it has are one fact about an office. That
file is the thing to port, not to redesign.

**Frappe ships nothing that identifies a device.** `User Session Display` has an
ip address and a user agent; `Activity Log` has an ip address. A user agent is
shared by a hundred million identical phones. There is no WebAuthn in v17 and
no device registry. So device identity is ours, and §6 says what it can and
cannot be worth.

## `attendance_device_id` is not what it sounds like

It is the number a *biometric terminal* knows somebody by — the id that arrives
on `Employee Checkin.device_id` when a ZKTeco or ESSL box syncs its logs. It is
not an asset tag and not a phone. Sites that own terminals need it and it stays
exactly as it is. It is the wrong field for anything below, and the temptation
to reuse it is the temptation to make one field mean two things.

## The layers

Each answers one lie. The column that matters is the last one: a layer that
**refuses** stops somebody at the door, and a layer that **flags** lets them in
and tells HR. Refusing on a probabilistic signal is how an attendance system
becomes the thing everybody hates.

| The lie | The layer | Setup cost | Refuse or flag |
|---|---|---|---|
| "I was at the office" — wasn't | geofence, `Shift Location` + radius | one click, uses the browser's position | refuse |
| "I was at the office" — in the car park, on mobile data | network: the office's public egress | one click, "use the address I am on now" | refuse |
| "my friend pressed it for me" | bound device | nothing, first use registers | refuse or flag, per policy |
| "I pressed it at nine" | the server's clock, never the browser's | none | refuse |
| "I scanned it from home" | a rotating code on a screen at the door | a tab open on any screen | refuse |
| "I was here all day" | a forgotten check-out, auto-closed and nudged | none | flag |
| "I was in two cities in ten minutes" | impossible travel, computed from rows we already have | none | flag |
| "the position was a bit off" | accuracy, recorded as reported | none | flag |

The four worth arguing for:

**A rotating code at the door** is the strongest layer per pound spent and the
one nobody builds. A tab open on a screen in the office — a spare monitor, a
tablet, a phone in a stand — shows a QR that changes every thirty seconds and is
a signed short-lived token. Scanning it proves presence in the room, because the
code cannot be forwarded and is stale by the time it is. It needs no hardware
that an office does not already have, and it composes with the geofence rather
than replacing it. A *printed* QR is not this: a printed code is photographed
once and used forever, so a static code is only ever a convenience on top of a
geofence.

**An NFC sticker at the door** is the same idea for a pound. A tag holds a URL,
every phone since 2018 reads one without an app, and the URL carries the place.
It is weaker than the rotating code — the URL can be copied — so it pairs with
the fence.

**Impossible travel and accuracy** cost nothing because every check-in already
carries a position and a time. Two logs four hundred kilometres apart twenty
minutes apart is not a refusal, it is a row in a review queue. So is a position
the browser reported with a two-kilometre accuracy radius, which is what a
desktop with no GPS reports and also what a spoofer reports.

**The review queue is the feature.** Every layer above writes what it saw
whether or not it refused. A month of "checked in from an unknown device, two
hundred metres out, at 08:59" is a conversation a manager can have. A month of
silent refusals is a month of people ringing HR from the car park.

## Who is doing the checking in

This is the hard constraint and it decides the shape of everything else. Three
populations, and pretending they are one is how these systems end up phishable.

**People with a login.** They check in from the desk or the phone, signed in as
themselves. Everything in §5 and §6 applies. This should be most of them.

**People without a login, with a phone.** An employee with no `User` has no
identity the server can check, so there is nothing to bind and nothing to
refuse — anybody holding the link is them. The honest answer is that they get a
login. A Website User costs nothing, carries no desk access, and is what HRMS's
own PWA already assumes. "Self check-in" and "has an account" are the same
decision and the setup should say so in one sentence rather than pretending
otherwise.

**People without a phone.** A shared tablet by the door in kiosk mode, where
each person identifies themselves — a PIN, or their own printed code scanned by
the tablet. The kiosk is a *place*, authenticated once as itself; the person is
authenticated by what they know or carry. This is the factory and retail answer
and it is the one case where a shared device is correct rather than a hole.

Which leaves the fourth: **nobody checks in at all**, and a supervisor marks the
roll for their team. Not a layer, but for some workplaces it is the only true
thing, and the product should support it without calling it attendance
tracking.

## Binding a device, honestly

There is no device identity in a browser. What there is:

- a random token we generate on first check-in, keep in `localStorage` **and** in
  a long-lived cookie we set, and register as a row against the employee;
- the user agent and the address, recorded alongside it as corroboration, never
  as identity.

The policy is one field with three values, and **trust on first use** is the
default because it costs the workspace nothing:

- **any** — no binding. Recorded, never enforced.
- **first wins** — the first device to check somebody in becomes theirs. A
  second device is refused with "this is not the phone you check in on", and HR
  can clear it in one click when somebody buys a phone.
- **approved** — a new device is registered as Pending and refused until
  somebody approves it. For sites that mean it.

**What this buys and what it does not.** It raises the cost of a favour from
"tell me your password" to "hand me your unlocked phone, twice a day, for
months". It does not stop a determined pair of colleagues and nothing short of a
face in front of a camera does. Saying so in the setup screen is better product
than implying otherwise.

**Passkeys are the honest end state.** A WebAuthn credential is held in the
phone's secure element and released by *the phone's own* face or fingerprint
check. We never see a biometric, never store one, never carry the liability —
the device does the work and tells us it was the owner. It is the fingerprint
reader everybody already owns. Frappe has no WebAuthn, so it is real work rather
than a switch, and it belongs at the end of the stages rather than the start.

## Phone, office PC, kiosk

"Should it be mobile only?" No, and the instinct behind the question is worth
taking apart.

A check-in from a desktop in the office, on the office network, at a fixed
address, is *more* corroborated than one from a phone, not less — the phone is
the surface that can be anywhere. What makes the phone feel safer is that it is
personal, and that is the binding layer's job, not the form factor's.

So the surface is a setting and not a rule: **desk, phone, kiosk**, any
combination. A workplace where everybody has a computer should allow the
computer. What is worth refusing by default is the *shared* desktop, which the
device binding catches anyway — the second person to use it is on somebody
else's registered device.

## The day: home, offsite, halves and pauses

**Home office.** The layers are per assignment and not global, which falls out
of putting them on `Shift Location`: a shift with no location has no fence and
no network rule, so somebody working from home presses the same button and is
refused nothing. The day is marked Work From Home through `Attendance Request`,
which HRMS already writes, and the record already draws it as its own colour.

**Offsite and field work.** A shift whose location is set but whose policy says
"field" should record the distance and flag it rather than refuse: a plumber
three miles from the depot is working, and a system that refuses them at a
customer's house is a system they will stop using. Same data, different verb.

**Half days.** Not ours. `Shift Type.working_hours_threshold_for_half_day` reads
the pairs and decides, and `half_day_status` on Attendance says which half
counted. What we owe the half day is *a check-out that actually happened*: the
single biggest cause of a wrong half day is somebody who forgot, so the shift
end auto-closes an open log and sends one nudge, and the auto-closed log is
flagged as such rather than silently equal to a real one.

**Pauses.** A break is already expressible — `Shift Type` can sum every valid
IN/OUT pair rather than the first and last, so lunch is an OUT and an IN. What is
missing is *why*, and a day of unexplained gaps is unreadable. One custom field
on `Employee Checkin` — break, lunch, errand, end of day — offered on the way
out and never on the way in, which makes a day's row legible and costs nothing
to compute.

## Where each setting lives

The rule: a switch that is true of the whole workspace goes on `HR Settings`; a
rule that is true of a *place* goes on `Shift Location`; a fact about a person's
phone is a row of its own.

**`HR Settings`, custom fields.** Self check-in on or off; which surfaces are
allowed; the device policy (any / first wins / approved); whether a forgotten
check-out is auto-closed; whether to require a reason on the way out.

**`Shift Location`, custom fields.** The networks (already designed, one range
per line); whether this place issues a rotating code; whether this place is a
fence or a field site.

**One new doctype, `Employee Device`.** Employee, label, token hash, status
(Pending / Trusted / Blocked), first seen, last seen, last address, last user
agent. One row per phone. This is the thing that is genuinely missing and cannot
be a custom field, because a person can have two and a table has to be queryable
from the check-in path.

**Possibly a second, `Checkin Kiosk`.** A place, a name, and a long-lived token
for the tablet. Only if the kiosk stage happens; a kiosk that is just a browser
signed in as a service account may be enough.

Nothing else is new. Every check-in is still an ordinary `Employee Checkin`
document with HRMS's own validation running — no `ignore_permissions`, no second
writer, no reimplementation of the shift maths.

## Stages

1. **The policy, and the switch.** The custom fields above, a setup screen that
   explains each layer in a sentence, and self check-in off by default.
2. **Place and network.** Port `place.py`: the one-click "use where I am" and
   "use the network I am on", and the refusal that reads them.
3. **The device registry.** `Employee Device`, trust on first use, and the
   sentence in the setup screen that says what it is worth.
4. **The record of what was seen.** Every check-in carries address, position,
   accuracy, device and surface, whether or not anything refused.
5. **The review queue.** Unknown device, impossible travel, poor accuracy,
   auto-closed. A screen that is a list of questions, not a list of refusals.
6. **The rotating code.** A page to leave open on a screen at the door, and the
   scan that resolves it.
7. **Breaks and the close-out.** The reason field, the shift-end auto-close, the
   nudge.
8. **Passkeys.** The fingerprint reader everybody already owns.

## What we are not building

- **Face recognition.** It is the obvious ask and it is a liability, a
  procurement conversation and a bias problem in one. A passkey answers the same
  question with the device's own biometric, which we never see.
- **A native app.** Everything above is a browser and a cookie.
- **Our own shift maths.** HRMS's is correct and on a schedule.
- **An SSID check.** There is no web API for it and there should not be.
- **Anything that trusts the client's clock.** The time on a check-in is the
  server's, always.
