# OneCalendar

Written by hand. What OneCalendar does and how to use it. Everything above
**Under the hood** is written for the people who use it, and OneAI reads it to
answer "how do I…" questions. Under the hood is for the people who build it.

OneCalendar is one calendar with everything dated in One on it: your meetings,
your to-dos, your deals' next steps, your leave, your interviews, the
company's holidays and who is off. Each is a **layer** you switch on and off.
Nothing is copied into the calendar — a deal's next step is the deal's, and it
moves when the deal does.

## Finding your way

**OneCalendar** in the dock opens the calendar. The rail has **Calendar**,
**Event** (every event as a list), and under **Setup** the
**Holiday List**, **Google Calendar** and **Calendar Links**.

The calendar shows a **Month**, a **Week**, a **Day** or a **List**; the
arrows move it and **Today** brings it back. It opens on the view you used
last, with the layers you left on, on any computer you log in from.

## Layers

On the left, in two groups:

- **Mine** — what is yours: **My Events** (ones you made, were invited to or
  were shared with you), **My Tasks** (assigned to you, on the day they are
  due), **Assigned to Me** (anything else you were given, a deal or a leave
  application, on the day it is due), **Deal Next Steps**
  and **Lead Next Steps** (on your own open deals and leads, at the time
  due), **My Leave** and **My Interviews** (the ones you are on the panel for).
- **Workspace** — what everybody shares: **Company Events**, **Holidays** (the
  company's holiday list, without the weekly days off) and **Who's Off**
  (approved leave; off until you switch it on).

**You only see what you may open.** Each layer reads its own records with your
permissions: somebody who cannot read leave has no Who's Off, and an employee
limited to their own record sees only their own leave there.

Clicking anything opens it: an event opens the event, a next step opens the
deal or lead, a task opens the task, and an assignment opens the record it is about.

## Events

**Add Event**, or drag across the hours you want, asks for a subject, when,
where and a description. Drag an event you made to move it, or its bottom edge
to make it longer; drag a task to move it to another day; a repeating event is changed from its own page, for all its
times at once. Everything else about an event — who is invited, reminders,
repeating, a video call link — is on the event's own page.

**Who sees an event:**

- a **private** event is seen by whoever made it, the people invited to it,
  and anybody it is shared with;
- an event **about a record** — its Reference, a link or an invited contact
  names a deal, a lead, an employee — is also seen, on Company Events, by
  everybody who may open that record. Clicking it opens the record; editing
  the event stays with whoever made it;
- a **public** event, **On Everybody's Calendar**, is seen by everybody. Only
  a Workspace Administrator or an HR Manager may make one; anybody else makes
  it private and invites the people it is for.

## A record's own calendar

**Calendar** on a project, a deal, a lead or an employee opens the calendar of
that one record: every event about it, including ones you could not otherwise
open (they open the record instead), and what it has with a date on it —

- a **project**: its tasks still to do, whoever is on them;
- a **deal** or a **lead**: its next step, whoever owns it;
- an **employee**: their leave, if you may see it.

**Add Event** there makes an event about the record. Nothing you switch off
there changes your own calendar.

## In Google, Apple or Outlook

**Subscribe** adds your calendar to another app: **Google Calendar**, **Apple
Calendar** or **Outlook** opens that app ready to add it, and **Copy Link** is for anything
else — a personal Outlook account pastes it under *Add calendar › Subscribe
from web*. It carries what the calendar shows before you switch any layer off,
from two months ago to a year ahead. How often the other app reads it again is
up to that app: Apple Calendar as often as you set in its settings, Outlook
every few hours, and Google a few times a day, on its own schedule. It only goes one way: an event you add in Google stays in Google.

**Anyone with the link can read your calendar.** **New Link** switches the old
one off, and **Switch Off** ends it. A Workspace Administrator can switch
anybody's off under **Setup › Calendar Links**, which shows when each was made
and last read.

For events that go both ways with Google, frappe's own **Google Calendar**
connection is under Setup; it needs a Google API key in Google Settings first.

## Under the hood

For the people who build OneCalendar. OneAI does not read past this heading.

### How it is made

- `layers.py` — the `one_calendar_layers` hook and the one read that merges
  them (`entries`). A layer is a dict: key, label, colour, group, whether it
  starts on, the doctype whose read permission it needs, and a `rows(start,
  end)` function in the module that owns the records. `entry` turns a row into
  what the page draws. A layer with a `move` can be dragged (`layers.move`
  hands the drop to it); one with `about` can draw a record's own calendar,
  which needs the reader to be able to open the record.
- `events.py` — frappe's Event, read here rather than through its
  `get_events`, for two reasons: frappe's permission hooks can only take access
  away, so "readable because of the record it is about" cannot be a hook; and
  `get_events` leaves out events a user is only a participant in.
  `occurrences` expands repeats; `validate` keeps Public to PUBLISHERS.
- `one_task/calendar.py` — tasks, and assignments on anything but a task.
- `one_crm/calendar.py`, `one_hr/calendar.py` — each module's own layers.
- `feed.py` — the subscription: a token per person, kept encrypted and found
  by its SHA-256, read as a guest and rate-limited, answered as that person. `calendar` writes RFC
  5545 by hand: UTC times, all-day dates, escaped and folded lines.
- `page/onecalendar` — the page, on the FullCalendar frappe already bundles
  for its own calendar view. The reader's layers and view are frappe user
  settings under Event.

### The plan

1. **The layers.** *Done.* A hook each module fills, and one merged read that
   copies nothing.
2. **Events and who sees them.** *Done.* frappe's rule, plus an event about a
   record visible to the record's readers, plus Public kept to publishers.
3. **The page.** *Done.* Month, week, day and list; layers in two groups;
   making, dragging and opening.
4. **The subscription.** *Done.* One link per person, for Google, Apple and
   Outlook.
5. **A record's own calendar.** *Done.* `?doctype=&name=` on the page, the
   layers that declare `about`, and a Calendar button (public/js/
   record_calendar.js) on a project, a deal, a lead and an employee.
6. **The old OneCalendar.** *Done.* OneApp's diary merged every screen with a
   calendar under a Mine and an Everyone lens, and derived any record's
   calendar from the record's tabs. The layers and their two groups are that
   merge; what it had that this did not was the calendar of a record other
   than a project, which is stage 5 now. It had no feed, no dragging and no
   events about a record, so nothing else was taken, and it is deleted.
