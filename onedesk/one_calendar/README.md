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
**Event** (every event as a list), **To Do**, and under **Setup** the
**Holiday List**, **Google Calendar** and **Calendar Links**.

The calendar shows a **Month**, a **Week**, a **Day** or a **List**; the
arrows move it and **Today** brings it back. It opens on the view you used
last, with the layers you left on, on any computer you log in from.

## Layers

On the left, in two groups:

- **Mine** — what is yours: **My Events** (ones you made, were invited to or
  were shared with you), **My To-Dos** (given to you, on the day they are
  due), **My Tasks** (assigned to you, on their end date), **Deal Next Steps**
  and **Lead Next Steps** (on your own open deals and leads, at the time
  due), **My Leave** and **My Interviews** (the ones you are on the panel for).
- **Workspace** — what everybody shares: **Company Events**, **Holidays** (the
  company's holiday list, without the weekly days off) and **Who's Off**
  (approved leave; off until you switch it on).

**You only see what you may open.** Each layer reads its own records with your
permissions: somebody who cannot read leave has no Who's Off, and an employee
limited to their own record sees only their own leave there.

Clicking anything opens it: an event opens the event, a next step opens the
deal or lead, a to-do opens the record it is about.

## Events

**New Event**, or drag across the hours you want, asks for a subject, when,
where and a description. Drag an event you made to move it, or its bottom edge
to make it longer; a repeating event is changed from its own page, for all its
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

## In Google, Apple or Outlook

**Subscribe** adds your calendar to another app: **Google**, **Apple** or
**Outlook** opens that app ready to add it, and **Copy Link** is for anything
else — a personal Outlook account pastes it under *Add calendar › Subscribe
from web*. It carries what the calendar shows before you switch any layer off,
from two months ago to a year ahead, and the other app reads it again about
every hour. It only goes one way: an event you add in Google stays in Google.

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
  what the page draws.
- `events.py` — frappe's Event, read here rather than through its
  `get_events`, for two reasons: frappe's permission hooks can only take access
  away, so "readable because of the record it is about" cannot be a hook; and
  `get_events` leaves out events a user is only a participant in.
  `occurrences` expands repeats; `validate` keeps Public to PUBLISHERS.
- `work.py` — ToDo and Task. Both move to OneTask when OneDesk has one.
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
5. **A record's own calendar.** The events about a deal, an employee or a
   project on that record's page, from the same read.
6. **The old OneCalendar.** Read OneApp's calendar after this one is built,
   take what it had that this does not, and delete it.
