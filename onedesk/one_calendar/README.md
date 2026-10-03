# OneCalendar

OneCalendar shows everything dated in One on one calendar: your meetings,
tasks, deals' next steps, leave, interviews, the company's holidays and who's
off. Each kind is a **layer** you can switch on and off.

Nothing is copied into the calendar. A deal's next step belongs to the deal,
and moves when the deal changes.

## Finding your way

**OneCalendar** in the dock opens the calendar. The left column has:

- **New Event** at the top
- the layers
- **All Events** (every event as a list), **Deadlines** and **Subscribe** at
  the bottom
- **Setup**, with **Google Calendar** and **Calendar Links**, for those with
  access

Switch between **Month**, **Week**, **Day** and **List**. The arrows move
back and forward, and **Today** returns to today. The calendar opens on your
last view and layers, on any computer.

The workspace's weekly days off are lightly shaded, and holidays show in red
with their names. Changes made elsewhere, like a new event or a moved task,
appear without reloading.

## Layers

**Mine:**

- **My Events**: events you created, were invited to or that were shared
  with you
- **My Tasks**: tasks assigned to you, on their due date
- **Assigned to Me**: anything else assigned to you, such as a deal or a
  leave application, on its due date
- **Deal Next Steps** and **Lead Next Steps**: on your own open deals and
  leads, at the time due
- **My Leave**
- **My Interviews**: interviews where you're on the panel

**Workspace:**

- **Company Events**
- **Holidays**: the company's holiday list, without weekly days off
- **Who's Off**: approved leave, off by default

**You only see what you have access to.** Each layer uses your permissions.
Someone who can't read leave doesn't see Who's Off, and an employee limited
to their own record only sees their own leave.

Click anything to open it. A next step opens the deal or lead, a task opens
the task, and an assignment opens its record.

## Events

**New Event**, or dragging across the hours, opens a form with the subject,
time, location, people and description.

- **Invite** adds people in the workspace.
- **Guests** takes email addresses of people outside the workspace. Each gets
  an email invitation for their own calendar, and another if the event moves
  or is cancelled.

Clicking an event shows its details: time, location, organizer, who's
invited and their replies, and the description. It has **Join** for a video
call, **Open** for the event's page, and **Delete** if you're allowed.

**Moving events:**

- Drag an event you created to move it, or drag its bottom edge to change
  its length.
- Drag a task to another day to change its due date.
- A repeating event can only be changed from its own page, for all
  occurrences.

Invitees, reminders, repeats and video call links are set on the event's
page.

**Who sees an event:**

- A **private** event is seen by its creator, invitees and anyone it's shared
  with.
- An event **about a record**, such as a deal, lead or employee named in its
  Reference, a link or an invited contact, also shows under Company Events
  for everyone who can open that record. Clicking it opens the record. Only
  the creator can edit the event.
- A **public** event, with **On Everyone's Calendar** ticked, is seen by
  everyone. Only a Workspace Administrator or HR Manager can create one.
  Everyone else creates a private event and invites people.

## Notifications

- **Invited to an Event**: someone adds you to an event.
- **Event Changed**: the time or location of an event you're on changes.
- **Event Cancelled**: an event you're on is cancelled or deleted.
- **Starting Soon**: at the event's reminder times, or 10 minutes before if
  it has none.
- **Today's Events**: each morning, your events for the day. Not sent on a
  day with no events.

The person who made a change isn't notified of it. Each notification
appears in One, and by email or push as set in Settings › Notifications.

## Asking OneAI

The OneAI panel on the calendar offers:

- **What is on this week?**
- **Find a time to meet…**: finish the sentence with who to meet.
- **Plan my day**

OneAI reads your calendar as you see it. When finding a time, it only sees
when colleagues are busy, not what their events are. It suggests the event
on a card. **Approve** adds it to your calendar and sends the invitations.
Nothing is created or sent before that.

## A record's own calendar

**Calendar** on a project, deal, lead or employee opens a calendar for that
record. It shows every event about the record, including ones you can't
otherwise open (these open the record instead), and its dated items:

- **Project**: its open tasks, whoever they're assigned to
- **Deal** or **Lead**: its next step, whoever owns it
- **Employee**: their leave, if you can see it

**New Event** there creates an event about the record. Layers you switch off
there don't affect your own calendar.

## In Google, Apple or Outlook

**Subscribe** adds your calendar to another app:

- **Google Calendar**, **Apple Calendar** or **Outlook** opens that app,
  ready to add it.
- **Copy Link** is for any other app. In a personal Outlook account, paste it
  under *Add calendar › Subscribe from web*.

The link includes everything on your calendar with all layers on, from two
months ago to a year ahead. It only goes one way. An event added in Google
stays in Google.

How often the other app refreshes is up to the app. Apple Calendar uses its
own setting, Outlook refreshes every few hours, and Google a few times a
day.

**Anyone with the link can see your calendar.**

- **New Link** replaces the link and turns off the old one.
- **Switch Off** turns the link off.
- A Workspace Administrator can switch off anyone's link under **Setup ›
  Calendar Links**, which also shows when each was created and last synced.
- To turn links off for everyone, switch off **Calendar Links** under
  Workspace › General. All links are deleted, no one can create one, and
  Subscribe disappears. Switching it back on doesn't restore old links.

For two-way sync with Google, use frappe's **Google Calendar** connection
under Setup. It needs a Google API key in Google Settings first.

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
- `tell.py` — who is told of an event (invited, changed, cancelled, starting
  soon, and each morning), through the hub; guests mailed an iCalendar
  invitation. frappe's own morning mail is stopped on migrate. The types are
  `notifications.py`.
- `ai.py` — OneAI here: `my_calendar`, `busy_times` (times only) and
  `plan_event`, a Create card whose guests ride on Event's `one_guests`.
- `events.make` and `events.card` — New Event with its people, and an
  event's card.
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
