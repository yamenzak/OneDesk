# Clocking In

Employees clock in and out themselves from any phone or computer. There is no
machine to buy.

**Check In, in the bar at the bottom.** It sits at the bar's right end, with
{one_ai}, Timers and Notifications, and has a dot: green while you are
clocked in, grey while you are not, and amber once your shift has started
without you or you checked in after it. Until you check in it shows when your
shift starts, and hovering says "Check in by 08:00" or "Your shift started at
08:00". On {one_hr}'s Home the button says the same: Check in by 08:00, or Check
In (late). Ten minutes after the start, anybody not in yet is reminded once
(Not Checked In). The shift is your shift assignment for the day, else your
default shift. On a phone it is at the top of the panel. Click it to clock in
or out. It picks the right direction itself, and it does not appear for
somebody on leave or on a holiday, for anybody without an employee record, or
when the workspace has not turned self check-in on.

## Registering a Passkey

**Before the first clock-in, register a passkey on your phone.** It is a key
your phone keeps and unlocks with your face, fingerprint or PIN. Registering
has to be done on a phone, not a desktop computer, and that holds for every
employee whether or not the clock is on: one made on the office computer would
check them in the day the clock is turned on. At the office computer, *Sign in with a Passkey* shows a code to
scan with that phone, and the password still works.

**A computer that is yours at work.** Once you've signed in on it, the
workspace administrator sets it to **Assigned** to you in Settings → Workspace
→ Devices. Then Register This Device on your Sign-in page makes a second
passkey there, which signs you in and checks you in without the phone; Reset
Passkey retires it with the phone's. A **Shared** browser, like the reception
computer, never holds anybody's. Each employee has one
passkey; after that it works on your other devices too, because iCloud and
Google sync it. Every clock-in asks for your face or PIN again. Clocking in
from your laptop with the synced passkey is not flagged for that; a passkey
that stays on one phone turning up in another browser is.

**A lost or new phone.** The screen that refuses you has a button to ask HR
for a reset. HR sees what your new phone looks like next to your old one, and
resets it in one click.

**Clock Device** in the rail lists every registered passkey: whose it is, the
device, when it was registered and last used, and its status — **Active**,
**Reset** or **Blocked**. **Reset** on one, or **Reset Passkey** on the
employee record, lets the person register a new passkey at their next
check-in; the old one is retired, not deleted. **Block** stops them checking
in or registering another.

**Signing in with your passkey.** The same passkey signs you in: the login
page leads with *Sign in with a Passkey*, and no password is needed. A passkey
belongs to the login rather than the employee, so
anybody can have one; an employee's is also the one the clock reads, which is
why only HR resets it.

## What a Clock-in Checks

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

## Home Working and Clocking Out

**Working from home or somewhere else.** Ask for it first with an
**Attendance Request**. Once it is approved, being off the network and away
from every location costs you nothing on those days. A home network can also
be learned for one person, so home counts like the office.

**Clocking out** asks for a reason — Break, Lunch, Errand or Done for the day
— when the workspace turns that on. You can clock in and out several times a
day. If you forget to clock out, the day is closed at the end of your shift,
you get one reminder, and the log says it was closed automatically.

The reasons offered are kept under **Clock Reason** in the rail. Add one,
give it a description to show when it is picked, or untick **Enabled** to
stop offering it. Tick **Ends Shift** on the one that means not coming
back today; a day closed at the shift's end is filed under it.

## Places, Networks and Reviews

**{one_hr} fixes its own settings.** When the office router gets a new address,
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
or a range. Rows marked Proposed were learned by {one_hr}: open one and press
**Confirm** or **Reject**. A rejected one is never proposed again.
