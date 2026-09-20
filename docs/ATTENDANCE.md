# Attendance without a machine

Written by hand. A plan, not generated reference.

An employee presses **Clock in**. No terminal, no fingerprint reader, no app.
What makes the press mean something is three gates — the device, the network,
the place — each switchable on its own and each cheaper to set up than the one
after it. A fourth, a live photo, is optional and answers a different question.

The gates run in order and stop at the first failure, so a workspace that turns
on only the first gets the first. None of them is new science, and most of the
parts are already on the bench.

## What already exists, and is therefore not ours to write

**HRMS ships the geofence.** `Shift Location` carries a position and a
`checkin_radius`; a `Shift Assignment` points an employee's shift at one;
`EmployeeCheckin.validate_distance_from_shift_location` refuses past it, gated
on `HR Settings.allow_geolocation_tracking`. It works. What it never had was a
screen that asked the browser for a position.

**HRMS ships the day's arithmetic.** `Shift Type` turns the check-in pairs into
a day: `working_hours_threshold_for_half_day`, `..._for_absent`,
`late_entry_grace_period`, `early_exit_grace_period`,
`working_hours_calculation_based_on`, and `enable_auto_attendance` to run it.
Half days, late marks and early exits are theirs. We compute none of them.

**HRMS ships the exceptions.** `Attendance Request`, with `reason` of *Work From
Home* or *On Duty*, a date range and a half-day flag.

**OneApp already wrote the network gate**, in `oneapp/onehr/place.py`. Its
argument holds: a browser cannot read an SSID and never will, so "the office
wifi" is honestly "the address we see you arriving from", read from
`frappe.local.request_ip` and never from a header the caller sets.

**Frappe ships nothing that identifies a device.** `User Session Display` has an
address and a user agent; a user agent is shared by a hundred million identical
phones. There is no WebAuthn in v17. So gate 1 is entirely ours.

## Gate 1 — the device

**The rule: a device belongs to one employee, and only that employee.**

The first time somebody clocks in, the browser makes a random secret, keeps it,
and the server stores it as a row: this device is Rania's. From then on every
clock-in carries it.

When the secret does not match, the clock-in **still goes through** and a flag
is written, and the screen says so plainly: *this is not the device you usually
clock in on — if you have changed phone, tell HR.* Refusing here would mean a
new starter with a new phone standing outside unable to start work, which is
worse than the thing it prevents. A workspace that wants a refusal can have one;
it is not the default.

**What this gate actually stops** is the shared office PC. One person signing in
as five colleagues and clocking them all in fails, because that browser's secret
belongs to the first of them and the other four each produce a flag naming the
same device. Five flags on one device inside ten minutes is not a subtle signal.

**What it does not stop** is somebody handing over their unlocked phone. Nothing
short of a face in front of a camera does, which is gate 4.

A device is one browser profile on one machine. A person who clocks in from a
phone and sometimes a laptop has two, which is fine: the rule is that a device
has one owner, not that an owner has one device. HR sees the list and can retire
one in a click.

## Gate 2 — the network

The address the request arrived from has to be in the office's list. One click
in setup fills it in: *use the address I am on now*. Ranges are allowed, one per
line.

Two things to say in the setup screen rather than discover later. A small
office's internet line may have a **dynamic address** that changes when the
router reboots, so the gate has to notice a run of failures and say "your office
address looks like it changed, here is the new one" instead of locking everybody
out on a Monday. And **mobile data is never the office**, which is the point, but
it means a workspace that turns this on has told its staff to be on the wifi.

## Gate 3 — the place

The browser asks for a position and the server checks it against the fence
HRMS already enforces. This gate needs the employee's permission, and the
browser will ask them for it, once.

Three details that decide whether it is usable:

- **Permission denied** is a policy, not an error. Default to a flag, not a
  refusal, because a denied prompt on somebody's first day is a support call.
- **Accuracy is reported and recorded.** A desktop with no GPS answers with a
  two-kilometre radius, and so does a fake. Anything vaguer than the fence is a
  flag even when the coordinates land inside it.
- **A rooted phone can lie about its position**, and there is no defence in a
  browser. This is why the gates are a stack rather than one clever check.

## Gate 4 — the photo, and why it is not a metadata gate

The idea was a photo as a *carrier*: the employee snaps anything at all, a black
frame or the ceiling, and we read the EXIF for the time, the device and the
position. It does not work, and it is worth writing down why so nobody proposes
it again.

- **Position.** A canvas capture carries no EXIF at all. A photo that does carry
  EXIF came from a file, iOS strips the location from files handed to a web page
  unless the person granted photo-location separately, and EXIF is plain text a
  person can write anything into. So the position is either absent or forged.
- **Time.** EXIF's timestamp is the phone's own clock, set by the phone's owner.
  The server already knows what time the request arrived, which is the only
  clock worth reading.
- **Device.** The browser hands over the camera label, the model string on
  Android Chrome, the WebGL renderer and the screen size on the same request as
  anything else — no file, nothing to edit.

So all three things the photo was going to carry are already known, and known
better. And without the position, the picture itself proves nothing: the same
black frame photographs identically from the car park, from home, and from bed.
As a metadata gate it is out.

**What a photo can still do, if a workspace wants it, is answer *who*** — which
is a different feature and should be described as one. A live frame from
`getUserMedia` (no file input anywhere, so nothing can be picked from the
gallery), shown to a human in the review list beside the employee's own profile
photo. No face recognition, no template, nothing computed. It is a deterrent
because people know somebody glances at it, and evidence when somebody does.

That is optional, it is off by default, and it is the only reason to build a
camera into this at all. The gates that do the work are the three above.

## Sites, and more than one fence

For a construction company, a shift is not one place.

HRMS is nearly there and stops short in a way worth knowing:
`validate_distance_from_shift_location` collects **every** Shift Location
assigned to the employee for that shift — and then checks `[0]`. The list is
built and thrown away. Checking all of them and passing on any is a few lines,
and it is the difference between one fence and a set.

On top of that, one Shift Location gains a child table of **other places this
shift may clock in from**: the depot plus every live site, maintained in one
record rather than by giving somebody four overlapping shift assignments.

And for genuine field work — a plumber at a customer's house — the fence is the
wrong verb. A place marked as a **site** records the distance and flags it
instead of refusing, because a system that locks people out at a customer's door
is a system they stop using.

## Home office, and how many times a day

**Working from home**, the shift has no location, so gates 2 and 3 do not apply
and the person just presses the button. The day is marked Work From Home through
`Attendance Request`, which HRMS already writes.

**Should they clock in more than once?** The mechanism is already there and does
not need building: `Shift Type.working_hours_calculation_based_on` can sum every
valid IN/OUT pair rather than the first and last, so lunch is an OUT and an IN
and the hours come out right. Whether a workplace *requires* that is a sentence
in their policy, not a feature in ours.

What we should not build is a prompt that pings somebody at random to prove they
are still working. It measures presence at a screen rather than work, everyone
knows it, and the first thing it produces is a culture that games it.

What we *should* build is the opposite: a day that is closed properly. The
single biggest cause of a wrong half day is somebody who forgot to clock out, so
the shift end auto-closes an open log, sends one nudge, and marks the closed log
as auto-closed rather than letting it look like a real one.

Alongside it, one field on the way out — break, lunch, errand, done for the day
— which costs nothing and makes a day of gaps readable.

## What gets refused and what gets flagged

The dividing line: **refuse on what is certain, flag on what is a guess.**

Refuse: the network is wrong. The position is outside a fence that is a fence.

Flag: an unfamiliar device. A denied location prompt. A position whose accuracy
is vaguer than the fence. Two clock-ins far apart in little time. Several people
on one device. An auto-closed day.

A month of flags is a conversation a manager can have. A month of silent
refusals is a month of people ringing HR from the car park, and it is how these
systems get switched off.

## Where each setting lives

A switch true of the whole workspace goes on **`HR Settings`** as a custom
field: self clock-in on or off, which gates are on, whether an unknown device
refuses or flags, the photo policy and its retention, auto-close on or off.

A rule true of a **place** goes on `Shift Location`: the address ranges, the
other places this shift may clock in from, whether this is a fence or a site.

A fact about a **phone** is a row of its own — `Employee Device`: employee,
label, hashed secret, status, first seen, last seen, last address, last user
agent. This is the one genuinely new doctype. `attendance_device_id` on Employee
is **not** it: that is the number a biometric terminal knows somebody by, it
arrives on `Employee Checkin.device_id` when a box syncs its logs, and reusing
it here would make one field mean two things.

Every clock-in is still an ordinary `Employee Checkin` document with HRMS's own
validation running. No `ignore_permissions`, no second writer, no
reimplementation of the shift maths.

## Stages

1. **Gate 1 and the settings.** `Employee Device`, register on first use, flag
   on mismatch, one owner per device. The switches, and self clock-in off by
   default.
2. **Gate 2.** Port `place.py`: one click to learn the office address, the
   refusal that reads it, and the dynamic-address warning.
3. **Gate 3.** Ask the browser for a position, record accuracy, and make HRMS's
   fence reachable for the first time.
4. **The review queue.** Every flag above, in one list, with the photo when
   there is one. Without this screen the flags are theatre.
5. **The live photo, if wanted.** In-page camera, no file input, shown beside
   the profile photo, retention setting, off by default.
6. **Sites.** Check every assigned location rather than the first, the child
   table of other places, and the site-not-fence mode.
7. **Closing the day.** Auto-close, the nudge, the reason on the way out.
8. **Passkeys.** The fingerprint reader everybody already owns, doing the
   biometric we never see.

## What we are not building

- **Face recognition.** Liability, bias, and a procurement conversation, to
  answer a question a passkey answers better.
- **A native app.** All of this is a browser.
- **Our own shift maths.** HRMS's is correct and already runs on a schedule.
- **An SSID check.** There is no web API for it and there should not be.
- **Anything that trusts the client's clock.** The time on a clock-in is the
  server's, always.
- **Random presence pings.** See above.
- **A photo read for its metadata.** The time, the device and the position are
  all known better without it, and without the position the picture proves
  nothing.
