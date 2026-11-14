# OneCalendar

The one file for agents, OneAI and us: what OneCalendar is made of, its
rules, where each file is, and the decisions that cost something. What
people read is in `help/`, one page per thing they do, shown in Help and
searched by OneAI's `how_to`; its versions are `updates/`. What is
known to be wrong and what is planned is `SCRATCHPAD.md` (docs/READY.md, A
module's folder).

OneCalendar shows everything dated in One on one calendar: meetings, tasks,
deals' next steps, leave, interviews, deadlines, the company's holidays and
who is off. Each kind is a layer a person switches on and off, and nothing
is copied: a deal's next step belongs to the deal and moves with it.

## Connections

- **From OneTask**: Your tasks show under My Tasks on their due date, and anything else assigned to you shows under Assigned to Me. Dragging a task to another day moves its dates.
- **From OneProject**: A project's own calendar shows its open tasks, including those of its sub-projects.
- **From OneCRM**: The next step on each of your open deals and leads shows at the time it's due. A deal's or lead's own calendar shows its next step.
- **From OneHR**: My Leave, My Interviews, Holidays and Who's Off come from OneHR. The holiday list also shades the weekly days off. An employee's own calendar shows their leave.
- **From OneInventory**: Asset maintenance that's due shows under My Maintenance and Maintenance Due.
- **From OneAI**: Deadlines read from bills and letters, a contract's last day to cancel and expiring employee documents show as layers. An appointment that arrives by mail or in a file becomes an event.
- **To One**: Home shows how many events you have today. Putting an event on everyone's calendar is OneCalendar's one ability, set in AccessCenter, and a OneCalendar Manager holds it (access.py).
- **To OneMail**: Guests outside the workspace get their invitations and cancellations by mail, sent through OneMail.

## Under the hood

### How it is made

- `layers.py` — the `one_calendar_layers` hook and the one read that merges
  them (`entries`). A layer is a dict: key, label, colour, group, whether it
  starts on, the doctype whose read permission it needs, and a `rows(start,
  end)` function in the module that owns the records. `entry` turns a row into
  what the page draws. A layer with a `move` can be dragged (`layers.move`
  hands the drop to it); one with `about` can draw a record's own calendar,
  which needs the reader to be able to open the record.

  A layer is one kind of dated thing: your events, your to-dos, your deals'
  next steps, who is off. Each module names its own in `hooks.py` under
  `one_calendar_layers`, as a list of dicts:

  - `key`, `label`, `color` — what the layer is called and drawn in.
  - `group` — **Mine** (what is yours) or **Workspace** (what everybody
    shares).
  - `on` — whether it is shown before the reader chooses.
  - `doctype` — the record the layer reads, which is also the permission it
    needs: a reader who cannot read Leave Application has no Who's Off layer.
  - `rows(start, end)` — a function returning dicts with `name`, `title`,
    `start`, and optionally `end`, `all_day`, `doctype` (when a row opens a
    different record than the layer's), `id` (when one record is on the
    calendar more than once), `editable`, `resizable` (when it may be dragged
    but not stretched), `about` and `description`.
  - `move(name, start, end, all_day)` — optional: what dragging a row does to
    its record. A row is only editable when its layer has one, and the
    function checks the reader may write the record, whatever the row said.
  - `about` — optional: the doctypes whose own calendar this layer can draw,
    or `["*"]` for any. On a record's calendar (**Calendar** on a project)
    only these layers are offered, and `rows` is called with a third
    argument, the `(doctype, name)` it is about. `only_about` keeps a layer
    off the main calendar and the subscription.

  **Nothing is copied.** A layer reads its own records through
  `frappe.get_list`, so a deal's next step is on the calendar of whoever may
  read the deal and of nobody else, and it moves when the deal does. The only
  records OneCalendar owns are Events, which are frappe's own.
- `events.py` — frappe's Event, read here rather than through its
  `get_events`, for two reasons: frappe's permission hooks can only take access
  away, so "readable because of the record it is about" cannot be a hook; and
  `get_events` leaves out events a user is only a participant in.
  `occurrences` expands repeats; `validate` keeps Public to whoever holds the
  publish ability (`may_publish`, access.py).

  An Event is frappe's: something at a time, with a subject, a place and the
  people it is with. frappe lets a person see a Public event, one they made,
  one shared with them, and one they are a participant in. **One adds a
  fifth: an event about a record is visible to whoever may read that
  record** — a meeting about a deal is on the calendar of everybody who may
  open the deal, as the deal itself is. An event is about a record when its
  Reference, one of its Links or one of its participants names it.

  Since this is not a hook, the calendar reads Events itself, in events.py,
  and shows such an event without opening it. Clicking it opens the record it
  is about. The Event's own form still follows frappe's rule, which is why
  editing one stays with the person who made it. Repeating events are
  expanded here too (`occurrences`), on the days shown.

  **A Public event is on everybody's calendar**, so making one is kept to the
  people who speak for the workspace: an administrator, or whoever holds
  **Put Events on Everyone's Calendar** (`calendar_publish`, a Permission Type
  on Event, a OneCalendar Manager's; the page reads it as
  `frappe.boot.one_calendar_publish`). frappe lets any desk user
  do it, and a calendar anybody can write on is a calendar nobody reads.
- `one_task/calendar.py` — tasks, and assignments on anything but a task.
- `one_crm/calendar.py`, `one_hr/calendar.py` — each module's own layers.
- `tell.py` — who is told of an event (invited, changed, cancelled, starting
  soon, and each morning), through the hub; guests mailed an iCalendar
  invitation. frappe's own morning mail is stopped on migrate. The types are
  in `notifications.py`, with each one's channels and sender.

  **On save** (`saved`, Event on_update): whoever was just added is told they
  are invited; if the time or the place changed, everybody already on it is
  told; an event set to Cancelled is a cancellation. **On delete**
  (`removed`) it is a cancellation too. Whoever made the change is never told
  of it.

  People inside the workspace are told through the hub, in their language and
  by the channels they chose. A guest, somebody outside, is mailed with the
  event attached as an iCalendar invitation (`invitation`), so it lands in
  their own calendar: a request when invited or changed, a cancellation when
  cancelled, each with a newer SEQUENCE so their calendar replaces the last.

  **Starting soon** (`soon`, every five minutes): each event's own reminders
  (frappe's reminders table on the event), or ten minutes before when it has
  none, told once per time it happens. **Each morning** (`today_events`)
  every person with something on their calendar that day is told what, from
  the same read the calendar makes for them. frappe's own morning mail is
  stopped (`install`): it went around the hub, in frappe's template, and left
  out events a person is only invited to.
- `agent.py` — OneAI here: `my_calendar`, `busy_times` (times only) and
  `plan_event`, a Create card whose guests ride on Event's `one_guests`.
  The calendar is read as the reader, through the same merge the page draws
  (`layers.entries`), so OneAI sees on it exactly what they do. A colleague's
  calendar is never read, only when they are busy, from the events they are
  on, without what those are. An event is only ever suggested; approving the
  card makes it, and the people on it are told then (`tell.py`), not before.
- `events.make` and `events.card` — New Event with its people, and an
  event's card.
- `feed.py` — the subscription: a token per person, kept encrypted and found
  by its SHA-256, read as a guest and rate-limited, answered as that person. `calendar` writes RFC
  5545 by hand: UTC times, all-day dates, escaped and folded lines.
  `settle` stores Calendar Links as on wherever nothing is stored yet. frappe
  reads a single's field nobody has saved as 0, so the first save of System
  Settings for anything else stored 0, switched links off and deleted them.
  The demo showed it.

  Google Calendar (*From URL*), Apple Calendar (*New Calendar Subscription*)
  and Outlook (*Subscribe from web*) all read the same thing: an iCalendar
  file at an address. The file asks to be read again every fifteen minutes;
  Apple and Outlook take that as a guide, and Google ignores it and reads on
  its own schedule, a few times a day. Each person has one address, with a
  secret in it, and whoever holds the address reads that person's calendar.
  The secret is kept encrypted, as frappe keeps an API secret, so the dialog
  can show the link again; a link is found by the secret's hash, and a new
  one switches the old one off.

  It carries the layers that are on before anybody chooses, read as that
  person, so it holds nothing they could not see on the calendar itself. It
  is one way: an event added in Google stays in Google. frappe's own
  two-way Google Calendar and Google Contacts sync is not offered: both are
  closed to everybody (`one/access.py` `_no_google`) and their fields hidden
  on Event and Contact.
- `page/onecalendar` — the page, on the FullCalendar frappe already bundles
  for its own calendar view, in the window: New Event is the page's primary
  action, the days and views are the command row, and the layers are a tree
  of check rows in the rail (`window.tree`). The reader's layers and view
  are frappe user settings under Event.
- `events.maintenance_visit` — ERPNext titles each visit a maintenance
  schedule books "Reference: …, Item Code: … and Customer: …"; it is titled
  with the visit and the customer, and the patch
  `maintenance_visits_named` titles the ones booked before.
- `access.py`, `notifications.py`, `setup.py`, `tour.py` — the READY
  mechanisms: the publish ability and its two roles, the seven kinds of
  notification, no setup steps, and the calendar's tour.
- `public/js/one_calendar/calendar_control.js` — its settings (Your Calendar
  Link) and its foot, drawn by the window as One's are.

## The plan

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

### planner.py

An appointment OneAI read, as an Event for whoever it is for (`event`). OneCalendar has no roles and so no agent: OneProject's coordinator makes it (one_project/agent.py `PLANS`).
