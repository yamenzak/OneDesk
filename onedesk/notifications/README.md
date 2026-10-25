# Notifications

Every notification and mail One sends is one file here, under the module that
sends it: `one_project/hours_over_plan.md` is OneProject's Hours Over Plan.
The file holds what the notification is, who it goes to, and its words. The
workspace changes its own copy on Settings › Notifications, and Reset brings
the file's words back.

## A file

    ---
    name: Birthday
    app: OneHR
    roles: Employee
    about: On the morning of a colleague's birthday.
    to: Everybody else at their company
    replaces: HR Settings.send_birthday_reminders
    starts_as: HR Settings.send_birthday_reminders
    ---

    # It is {employee}'s birthday today

    Wish them a happy birthday.

The header comes first, one key a line, always in the order below. Then the
subject, as the heading, and the message. A message is HTML on one line, so
its lines are joined with a space. After a line that ends in `<br>` the next
follows straight on, so a mail's paragraphs can stand apart. A name in braces,
`{employee}`, is filled in when it is sent, and an administrator writes it as
`{{ employee }}`.

The file is written in exactly this layout (`layout.py`), and the tests hold
it to that. The file is named for the type, in lower case with underscores.

| Key | What it says |
|---|---|
| `name` | The notification's name, as Settings › Notifications lists it |
| `app` | The app it is listed under |
| `roles` | Only people with one of these roles may choose how they get it |
| `about` | When it is sent, from the reader's side |
| `to` | Who it is sent to |
| `button` | Its mail's button, when "Open" and the record's kind would not say it. A mail to an outside address draws it to the `link` (or `url`, `account`) it is sent with |
| `email`, `push` | `no` when it is never mailed, or never pushed |
| `email_default`, `push_default` | Mailed, or pushed, to everybody until they choose otherwise |
| `outside` | It goes to addresses outside the workspace, so only by mail |
| `required` | It can't be turned off |
| `always_mailed` | Mailed whatever the person chose, as a security notice is |
| `from_one` | Sent by One about itself (its plan, credits, storage, billing), so its mail wears One's mark and colour rather than the workspace's. Every mail from the admin site does |
| `oneai` | Written as OneAI |
| `follows` | The same event said another way. It takes the choices of the one it follows |
| `words`, `rule` | A rule the stock, accounts or HR records already had, told on the bell in its own words |
| `notification` | The Notification of ours that mails it. Its Enabled box and Send This are one |
| `mailed_by` | Its app mails it, and One lists it so everything sent is on one page |
| `switch` | The app's own setting that is its Send This |
| `replaces` | The app's own settings it stands in for. They are turned off and hidden |
| `starts_as` | It starts on only if this setting of the app's was on |

## Channels, senders and how each looks

A module on its way to ready (`onedesk/one/ready.py`) declares its types in
its own `notifications.py` rather than in files here, and each says two more
things (`layout.py`, docs/READY.md mechanism 8):

- **`channels`**: `bell`, `email` and `push`, each `True` or a sentence
  saying why it doesn't go that way ("Mail is what failed, so it isn't told
  by mail."). Telegram joins the list when it is built. `layout.settle`
  turns a channel that's off into `email: no` or `push: no`.
- **`sender`**: `system`, One about itself (its plan, credits, storage),
  wearing One's mark; or `workspace`, wearing the workspace's name and
  colour. It replaces `from_one`.

How each channel shows one is written down once, in `layout.py`:

| Channel | Shows |
|---|---|
| Bell | The subject, as one line of at most `BELL_LINE` (120) characters |
| Email | The framed layout (`one/notify.py` `compose`), from One or the workspace by its sender |
| Push | The subject as its title, cut at `PUSH_TITLE` (65), and the message as its body, cut at `PUSH_BODY` (180), on a whole word (`layout.cut`) |

## Adding one

1. Write its file under the module that sends it.
2. Send it by name, with `notify.notify` to people in the workspace or
   `notify.mail` to an address outside it.
3. Migrate. Each file becomes a Notification Type, listed on Settings ›
   Notifications.
4. Translate its words. They are read from the file like any other string.

## Connections

- `one/notify.py` is the one door everything goes out through. It makes each
  file a Notification Type after every migrate, and draws every mail
  (templates/emails, The mail below).
- Each module's `tell.py` decides when, and sends by name.
- `one/rules.py` carries rules to the bell: the ones the stock, accounts
  and HR records came with, and the workspace's own.
- Settings › Notifications lists every file by app, and a person's own
  Notifications page lists the ones they may choose.
- `babel.py` reads a file's words for translation.

## Under the hood

### layout.py

The layout is the one under A file. The header says what the type is and who
it goes to, one key a line, always in the order of `KEYS`. Below it, the
subject is the heading and the message is the rest. A message is one line of
HTML: its lines are joined with a space, and straight on after a line that
ends in `<br>`, so a mail's paragraphs can stand apart. A type in its app's
own words, or mailed by its app, has neither.

### The hub

A notification is a row of frappe's own Notification Log, of a Notification
Type. There is no second notification system beside it.

- **Registered.** `hooks.py` names this folder once, under
  `one_notification_types`. After every migrate `notify.install()` makes each
  file a Notification Type, with its app, words and channels in the `one_*`
  fields of `custom/notification_type.json`.
- **Sent.** `notify.notify(name, users, record=..., link=..., **slots)` renders
  the type once per reader language and writes the bell through frappe's
  `enqueue_create_notification`. Frappe then mails whoever has the type in
  their `email_notification_types`. `push.pushed`, a Notification Log
  `after_insert`, queues `push.send` for whoever has it in
  `one_push_notification_types`. `notify.mail()` is for addresses outside the
  workspace and for mails people answer by replying. `tests/test_notify.py`
  refuses `frappe.sendmail` and any Notification Log write anywhere else.
- **Rendered.** `notify.render`. A file's words have named slots and are
  translated for each reader. Once an administrator edits them they are Jinja,
  sent as written, in a sandbox with no globals, and `notify.validate` refuses
  a name that is not one of the type's slots. Every value is escaped first.
  Names are bold in subjects.
- **Chosen.** Turning Email off for a type takes it out of everybody's
  `email_notification_types`. A new person starts with only the
  `email_default` types (`notify.new_person`). A `push_default` type is put
  into everybody's push list once (`seed_push`), and after that the choice is
  theirs. A type with `roles` is listed only to people holding one
  (`notify.choosable`).
- **Pushed.** Standard Web Push through `pywebpush`, with one VAPID key pair
  per site. Each browser is a Push Device row, made on Turn On Push. A message
  is only ever posted to the four services in `push.SERVICES`, and
  `push.worker` serves the service worker.
- **Rules.** `one/rules.py`'s `Rule` stands in for frappe's Notification
  (`override_doctype_class`). Each rule gets a type of its own, named after
  it and listed under Rules, and deleting the rule deletes the type. A rule
  saved by somebody without frappe's Notification roles is a workspace rule
  (`one_rule`), and `_hold` keeps it to the bell, filters rather than Python,
  one of seven events, and recipients by role, a person field or assignees.
  When it fires, only people who may read the record are told
  (`get_list_of_recipients`). ERPNext's and HRMS's own rules are told on the
  bell in their words by `Rule.send_an_email`, and only an address that is
  nobody here is still mailed.
- **Upstream switches.** A type that `replaces` an app's setting turns that
  setting off after every migrate and hides it. With `starts_as`, the type
  starts on only if the setting was on.

### The mail

Every mail the workspace sends is drawn one way: the workspace's name (and its
company's logo, when it is an image a mail client can show) above a white
card, with the footer under it. In the card, the heading says what happened,
then the message, one button to what it is about, and at the foot which
notification it is, when it is sent, and a link to change what the person gets
by mail.

- **Ours replaces frappe's frame.** `templates/emails/standard.html` and
  `email_header.html` are found before frappe's, because frappe's template
  loader searches the last-installed app first. So frappe's own framed mails
  (a password reset, a welcome) wear the same frame, and their header becomes
  the card's heading.
- **A mail somebody writes is not framed.** A message sent from a record or in
  OneMail goes as written, with only the footer.
- **A notification's mail is ours.** `notify.NotificationLog` mails each log
  through `notify.mail_log`: the subject as the heading, the button named for
  what it opens ("Open Supplier Quotation", or the type's `button`), and the
  type's name and `about` at the foot. Frappe's was "New Notification" and
  "Open Document".
- **A mail to an outside address** (`notify.mail`) has the same frame, without
  the settings link, since its reader has no settings.
- **Whose it is.** The masthead is the workspace's name and its company's logo
  (an SVG is left out, since almost no client shows one), and the button is the
  company's Brand Colour, with white or ink on it by contrast (`notify.ink`). A
  `from_one` type, and every mail from the admin site, wears One's mark
  (`images/one-mail.png`) and ink instead (`notify.one_mail_brand`).
- **Colours are written out.** A mail client reads none of our stylesheets or
  CSS variables, so the templates write frappe-ui's own values, and the token
  guard leaves `templates/emails` alone.
- **The subject line is plain text**: no tags, and `&amp;` as `&`
  (`notify.plain`).
- **Always mailed means mailed.** `notify.notify` mails an `always_mailed` type
  to each person itself, whatever they chose. That reaches somebody just
  switched off (a deleted account) and somebody told about their own action,
  whom frappe leaves off the bell. A sender that mails it its own way, like a
  project's update, passes `mailed=False`.
- **Right to left.** A mail to a reader of Arabic is drawn right to left
  (`rtl` in `standard.html` and `one_mail.html`).
