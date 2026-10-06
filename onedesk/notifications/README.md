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
| `email`, `push` | `no` when it is never mailed, or never pushed |
| `email_default`, `push_default` | Mailed, or pushed, to everybody until they choose otherwise |
| `outside` | It goes to addresses outside the workspace, so only by mail |
| `required` | It can't be turned off |
| `always_mailed` | Mailed whatever the person chose, as a security notice is |
| `oneai` | Written as OneAI |
| `follows` | The same event said another way. It takes the choices of the one it follows |
| `words`, `rule` | ERPNext's or HRMS's own rule, told on the bell in its own words |
| `notification` | The Notification of ours that mails it. Its Enabled box and Send This are one |
| `mailed_by` | Its app mails it, and One lists it so everything sent is on one page |
| `switch` | The app's own setting that is its Send This |
| `replaces` | The app's own settings it stands in for. They are turned off and hidden |
| `starts_as` | It starts on only if this setting of the app's was on |

## Adding one

1. Write its file under the module that sends it.
2. Send it by name, with `notify.notify` to people in the workspace or
   `notify.mail` to an address outside it.
3. Migrate. Each file becomes a Notification Type, listed on Settings ›
   Notifications.
4. Translate its words. They are read from the file like any other string.

## Connections

- `one/notify.py` is the one door everything goes out through. It makes each
  file a Notification Type after every migrate.
- Each module's `tell.py` decides when, and sends by name.
- `one/rules.py` carries ERPNext's and HRMS's own rules to the bell.
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
