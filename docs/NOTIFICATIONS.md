# Notifications

How frappe v17 notifies, what erpnext, hrms and OneDesk actually do, and the
plan for one way through for everything One sends. The rule is that every
notification One sends reaches people through this. A workspace administrator
decides what each one says and which channels it may use, each person decides
which of those channels they get it on, and an administrator can build new ones,
or ask OneAI to.

## What frappe v17 gives

**Notification Log is the hub.** Every in-app notification, the bell, is a
Notification Log row for one person. Inserting one:
- pushes it to that person's bell in realtime;
- marks their bell unseen;
- emails it to them if they chose email for its type (`send_notification_email`,
  template `new_notification`).

**Notification Type is new in v17.** `Notification Log.type` used to be a fixed
Select. It is now a Link to Notification Type, a doctype a site can add to.
Frappe ships five: Mention, Energy Point, Assignment, Share and Alert. A type
can be disabled. A type is only a category; it carries no text and no channels.

**Each person's Notification Settings** holds `email_notification_types`: the
types they also want by email. New types are off by default, and
`enable_email_for_all_users` turns one on for everybody. The older checkboxes
(mentions, assignments, shares and the rest) are still there. Our You ›
Notifications screen still shows those old checkboxes; it knows nothing of
types.

**The Notification doctype is frappe's builder.** A rule has:
- a doctype, and an event: New, Save, Submit, Cancel, a number of days or
  minutes before or after a date, a value changing, or a method;
- a condition, in Python or as filters;
- recipients, by field, role, owner or assignees;
- a Jinja subject and message;
- a channel: Email, Slack, System Notification (the bell) or SMS;
- a notification type, when the channel is the bell.

A System Notification rule creates Notification Logs of its type, so it goes
through the hub like anything else.

**Push is not wired to anything in frappe.** `frappe/push_notification.py` is a
client for a relay server (`push_relay_server_url`) that passes messages to
Firebase, with Push Notification Settings to turn it on. Nothing in frappe
calls it. HRMS uses it for its own mobile app, through its own PWA
Notification doctype.

## What actually sends today

Most of it does not go through the hub. It calls `frappe.sendmail`, or writes
the bell directly, with text fixed in code:

| | Direct `frappe.sendmail` | Bell written directly | Standard Notification rules | Uses Email Template |
|---|---|---|---|---|
| frappe | 25 files | 12 | 2 (both off) | 9 |
| erpnext | 12 | 2 | 2 | 6 |
| hrms | 7 | 1 | 4 | 5 |
| OneDesk | 3 | 16 (every one typed Alert or Share) | 1 (off) | 0 |

Three kinds, and each gets a different answer:

- **Customisable already**, through an Email Template chosen in a settings
  record:
  - HR Settings: leave approval and status, interview reminder and feedback;
  - Delivery Settings;
  - Appointment Booking;
  - Email Campaign;
  - System Settings: welcome and password reset.
- **Fixed in code**:
  - erpnext: project updates, reorder alerts, stock repost errors, email
    digests;
  - hrms: birthday and anniversary reminders, the daily work summary, the exit
    interview, emailed salary slips;
  - frappe: assignments, mentions, shares and document follow.
- **Rules**: the Notification records erpnext and hrms ship (training, exit
  interview, retention bonus, material request, fiscal year). They are
  editable, but email-only.

## The plan

**One hub: Notification Log and Notification Type.** It is frappe's own, the
bell already reads it, and email by type is already built on it. We add what
it lacks, on the type and on the person's settings, and never a second
notification system beside it.

**A type carries its text and its channels.** Custom fields on Notification
Type:
- the app it belongs to;
- a subject and a message, in Jinja;
- which channels it may use (In-app, Email, Push);
- which of those a new person gets by default.

Our own types ship with their defaults in code, the way frappe ships its five.
The administrator can edit them, reset them, or ask OneAI to rewrite them. The
bell is always on: it is the record of what was sent, so it is not a channel
anybody turns off.

**One door for our code.** `one/notify.py`, `notify(type, users, record,
context)`, renders the type's text and writes the Notification Log. Everything
else follows from the hub: the bell, email by the person's choice, and push.
Our sixteen direct writes move onto it, each with a type of its own rather than
Alert. A test then refuses `frappe.sendmail` and direct Notification Log writes
anywhere else in OneDesk.

**Each person chooses.** You › Notifications becomes a matrix: every type they
can receive, grouped by app, against In-app, Email and Push. Only the channels
the administrator allows can be ticked. Email writes frappe's own
`email_notification_types`, and push writes a matching list beside it.

**The administrator decides.** A new Workspace › Notifications screen:
- every type, by app: on or off, its allowed channels, its defaults, and its
  text, with a preview;
- the rules (the builder, below).

**Push.** A doc event on Notification Log sends it to the person's devices when
they chose push for its type. The transport is a decision to make (see below).

**The builder** is frappe's Notification doctype with a screen of our own:
- New Notification asks what the rule watches, when it fires, who receives it,
  and what it says;
- it defaults to the bell with a type, so people's channel choices apply to
  it too.

OneAI gets a suggestion tool, `draft_notification`, that turns "tell the account
manager when an invoice is seven days overdue" into a rule the administrator
approves. The type editor gets "Rewrite this".

**Everything already sending is brought in screen by screen, during the pass.**
Where erpnext or hrms has a setting to turn its own sending off, we turn it off
and ship a standard rule of the right type in its place. Where it has an Email
Template setting, the template stays, and the type's text points at it. Where
the text is fixed in code with no switch, it is listed in the screen's passover
entry and left until it matters.

## Stages

1. **The hub.** Done. `one/notify.py`, our own types, the custom fields on
   Notification Type, and our sixteen writes moved onto them. A test holds
   the door.
2. **The administrator's types.** Done. Workspace › Notifications: each type's
   channels, defaults and text, with a preview, reset, and OneAI's "Rewrite
   this".
3. **The person's choices.** You › Notifications as the matrix. The screen we
   are on now becomes this.
4. **Push**, on the transport chosen. Registering a device, sending on
   Notification Log, and its legal lines.
5. **The builder.** Rules on their own screen, with `draft_notification` for
   OneAI.
6. **Absorbing erpnext and hrms**, screen by screen, in the passover.

## The decision this needs

**How push reaches a device.**

- **Standard Web Push** (VAPID, `pywebpush`). Our server encrypts each message
  for the device (RFC 8291), so the browser's push service (Google's for
  Chrome, Mozilla's, Apple's) carries it without being able to read it. It
  needs no relay of Frappe's. It works in any desktop browser, and on phones
  once One is installed as an app (iOS 16.4 or later).
- **Frappe's relay.** It is what HRMS's app uses, but it needs Frappe's relay
  server set up for the site. The relay and Firebase both see the message, so
  both become subprocessors.

The recommendation is Web Push. Nobody new reads what we send, and it depends
on nothing but the browsers.

## Stage 1, as built

- **Twenty-five types, declared by the modules that send them**, each in its
  `notifications.py` and named in `hooks.py` under `one_notification_types`:
  eight in OneHR, six in Intake, ten in OneCloud, one in OneProject.
  `notify.install()` makes them Notification Types after every migrate.
- **A type's text has named slots**, `_lt("<b>{who}</b> shared <b>{file}</b>
  with you")`. Sent as it came, it is translated for each reader. An
  administrator edits it as Jinja, `{{ who }}`, and from then on it is sent as
  they wrote it. Every value is escaped before it goes in.
- **Two ways out.** `notify.notify()` writes the bell through frappe's own
  `enqueue_create_notification`, grouped by the readers' languages, and frappe
  emails it to whoever chose email for the type. `notify.mail()` is for the
  four OneCloud types that go to addresses outside the workspace (a file
  request, its reminder, a shared link, its code) and for the project update
  mail people reply to.
- **Defaults.** Email is on by default for what somebody has to act on: a
  letter asked for, a grievance, a new IBAN, phishing, the weekly digest, a
  shift not reading, somebody not marked Left, a file request complete.
  Everything else starts on the bell only.
- **What cannot be switched off.** The shared link's code (`required`), or
  nobody could open a link.
- **The project's own question.** A project with its own subject and message
  asks those instead of the type's text (`words=`), because somebody wrote them
  for that project.
- `tests/test_notify.py` refuses `frappe.sendmail` and any Notification Log
  write outside `one/notify.py`, and checks that every type sent is declared,
  that outside types are only mailed, and that slots are named.

## Stage 2, as built

- **Workspace › Notifications** lists every type by app, and opens one as a
  form: on or off, its subject and message with a live preview, and whether it
  may be mailed and is for new people. What it checks is in
  `docs/PASSOVER.md`.
- **An edited text is sandboxed.** It renders in a Jinja environment with no
  globals, and `notify.validate` refuses a text naming anything but the type's
  slots, however it is saved.
- **Names are bold in subjects** by `render`, so the default texts lost their
  `<b>`.
- **Email means email.** Turning it off for a type removes the type from
  everybody's `email_notification_types`; a new person's settings start with
  only the types marked for new people (`notify.new_person`).
- **OneAI** reads a type (`notification_type`) and suggests new text as a card
  (`rewrite_notification`), which the administrator applies.
- **Push** is on every type and hidden until stage 4 sends it.
