# OneStudio

Written by hand. What OneStudio does and how to use it. Everything above
**Under the hood** is written for the people who use it, and OneAI reads it to
answer "how do I…" questions. Under the hood is for the people who build it.

OneStudio is where a workspace's administrators make One work the way their
business does: **Extensions** that make a form behave the way you need,
**Custom Fields** to change what a form shows, and **Record Types** for the things
you keep that no app came with. You describe what you want to OneAI; it does
the making, and nothing changes until you approve it.

Only workspace administrators see OneStudio.

## Finding your way

**OneStudio** in the dock opens it. The rail has:

- **Extensions** — what OneAI has written for your workspace, on or off.
- **Custom Fields** — every field your workspace added or changed.
- **Record Types** — the kinds of record your workspace keeps of its own.

## Extensions

An extension makes a form do something it did not: refuse to save a customer
without a mobile number, fill in a field from another, warn when a discount is
over a limit, hide a field until another is ticked.

**Asking for one.** Open OneAI from Extensions and press **Write an
extension…**, or just say what you want: "Stop an invoice being saved
without a purchase order number." OneAI writes it, a second check reads what
it wrote against what it says it does, and you get a card saying what it
does. **Approve** turns it on. Nothing runs before that.

**Where it runs.** On the **screen**, it runs in the browser of whoever opens
the page, with their own permissions. On a **form** it can show, hide, fill in
or require a field, add a button, and tell the person something. On a
**list** it can label records (a red **Overdue**), change how a column reads,
and add a button. It can also look up another record to do it, as the person
would, but never change one from the screen. On the **server**, it runs whenever the record is saved, submitted,
cancelled or deleted, whoever does it and however: the form, an import,
OneAI, another app. Use the server for a rule that must always hold.

**On One's own pages.** An extension can also run on One's own pages, each
with its own few things it may do:

- **OneMail**, when a conversation is opened: show a note under it ("A key
  customer"), or add a button beside Reply. And whenever a message is
  written, anywhere in One: show a note above it, or fill in its subject, cc
  or bcc.
- **A record's head**, each time the record is opened or saved: add a button
  beside the head's own, a figure in its band ("Sales Invoices: 12"), or a
  note under it. Only on the kind of record you name.
- **OneCalendar**, when an event's card is opened: show a note on it, or add
  a button.
- **OneTask**, each time a view of your tasks is shown: a note or a button
  under its name ("4 of your tasks are overdue").
- **OneCloud**, when a file is chosen: a note or a button under its preview.
- **OneIntake**, when a document is opened in the inbox: a note or a button
  under its head.
- **The pipeline board**, each time what a stage is worth changes: a note
  above the board.
- **Every space's home** (One, OneCRM, OneHR, OneBook and the rest): a note or
  a button above its blocks.

Ask for one the same way: "When I open a conversation from anyone at
acmeco.example, show a note that they are a key customer." It is reviewed,
off until you approve it, and its errors are written down, the same as any
other. It never sees more of the page than what it is given, and it starts
running for each person the next time they load One.

**On a schedule.** An extension on the server can also run on its own,
every hour, day, week or month, or on a schedule you give ("each weekday at
eight"), at most once an hour: "every morning, add a comment to each open task
whose end date has passed." It works on the records it finds, not on one being
saved, and only on kinds of record you may open yourself.

**Checked before you see it.** Before an extension is kept, OneAI's code is
checked for what would make it fail: every field it names must be one the
record has, every form event one frappe calls, the screen code must read as
JavaScript, and it must be one change, not a hundred lines of them. Code for
the server is also run once on one of your records and undone straight away,
so an error shows now rather than on someone's next save, and OneAI is told
what it did ("it stopped the save, saying…"). Whatever is wrong goes back to
OneAI, which mends it before anything reaches you.

**What you see, and what you do not.** Each extension opens on whether it is
**On** or **Off** (or **Refused by Review**, or **Cannot Run Here**) and what
it does, then when it runs, what was asked and by whom, and its review. You do
not see its code, and nobody in your workspace writes or changes it by hand,
so there is nothing to type and no Save: OneAI writes it, and to change one you
press **Change this one…** on it and say what ("make it apply only to new
customers"). OneAI reads the code it has now and changes only what you
asked, keeping the rest as it was; it is reviewed again, and it stays off
until you approve it. Changing where or when it runs counts as changing it.

**Turning one on and off.** **Turn On** and **Turn Off** at the top of the
extension. One the review refused cannot be turned on; ask OneAI to change
it. Deleting an extension (**…** at the top) takes it away for good. The other
administrators are told when one is turned on, turned off or deleted, and by
whom: from that moment it runs on everybody's work, or no longer does.

**When one goes wrong.** An extension that runs into an error does not stop
anybody's work: on the server the record still saves, on the screen the form
goes on working. The error is written down, **Errors in the Last 7 Days** counts
it, and every morning the administrators hear of the extensions that ran into
one. The extension's **Errors** tab lists them: when, on which record, and what
went wrong in one line, since OneAI last wrote it. Press **Fix With OneAI**
at the top of the extension: OneAI reads the code and its errors, and a few
minutes later tells you what went wrong and that it has written a fixed
version, reviewed and off until you turn it on. Or ask **Has this one run into errors?**
in OneAI, or turn it off. An extension can also go wrong without an error:
one that never does its work logs nothing. Tell OneAI what it does wrong,
such as "Create Call Task never makes the task", and it fixes it the same
way. A message an extension means to stop a save with,
such as "A customer needs a mobile number", is not an error: it stops the
save, as it says.

**What an extension may not do.** Read or change what you could not; reach
outside your workspace (no mail, no calls to other services); change
frappe's own records or One's; run on a timer. OneAI says so when what you
ask needs one of these, and offers what it can do. For something on a
schedule, or that tells people, an **Automation** is the way.

**Server extensions** run only on workspaces where they are turned on. If an
extension says **Cannot Run Here**, ask us.

## Custom Fields

**Custom Fields** lists every field your workspace added to a form or changed
on it: the field, its form, its type, and the other forms it was also added
to. **Added** marks a field the workspace made, **Changed** a standard field
it changed. Filter by form, status or app, or search by name.

To add a field, click **Add Field** and tell OneAI what you need. It asks a
few questions, recommends the field type and properties, suggests related
forms that need the field too (for example Item fields on invoice and order
items), and makes one card to approve.

Click a field to open its form's **Customize** page: custom fields, changed
fields, the form header, connections and buttons, and extensions.
**Customize** on a form's own menu opens the same page. You don't edit
anything there. Ask OneAI to change or remove a field. See Customizing a Form
in One's documentation.

**Who sees and changes it.** Workspace administrators only, on the forms they
can open, and never the framework's own forms or One's. A change applies to
everyone who opens the form. The other administrators are notified
(**Form Customized**).

**OneAI** on the list says which forms were changed and how, or changes the
one you name. On a form it adds a field step by step, suggests changes as one
card, says what was changed and which extensions run on it, or explains how
customizing works. A check no field setting can say, it offers as an
extension.

## Record Types

A record type is a kind of record your workspace keeps that no app came with:
memberships, vehicles, rooms, contracts, inspections.

**Making one.** Open OneAI from Record Types and press **Make a record
type…**, or say "Make a record type for the vans we keep: registration,
make, mileage, the date we bought it and whether it is in use." OneAI designs
its fields, and the card shows its name, the app it belongs to and its
fields. **Approve** makes it.

**Where it lives.** In the rail of the app it belongs to, under **Your
Records**. The people who use that app make and change its records; its
managers delete them. A record type in **One** is everybody's.

**What it may have.** Text, numbers, money, percentages, dates and times,
ticks, choices, phone numbers, ratings, durations, files and pictures, and
links to a kind of record you may open, or to another record type. The first
text field names each record.

**Changing one.** Ask OneAI: "Add a colour to Company Van." A field you take
away is hidden, never deleted, so nothing anybody entered is lost. Its fields are listed in
**Custom Fields**, as for any other form.

**Deleting one.** Delete its records first: a record type that still has
records cannot be deleted.

## Being told

Every administrator is told, on the bell and by mail unless they chose
otherwise in their notifications:

- **Extensions Failing**, each morning, the extensions that ran into a
  error the day before. Not sent when none did.
- **Extension Turned On**, when another administrator turns one on: what it
  does, where and when it runs.
- **Extension Turned Off** and **Extension Deleted**, on the bell only unless
  you ask for mail.
- **Form Customized**, when another administrator saves a form's Customize
  page or resets it, on the bell only unless you ask for mail.

Nobody is told of their own change.

## Asking OneAI

On Extensions: **Write an extension…**, and **What do our extensions do?**,
which says what each does and whether any is failing. On an extension:
**Change this one…**; when it is on, **Has this one run into errors?**, which
reads what went wrong and on which record (never its code); when it is off,
**Why is this one off?** On Record Types: **Make a record type…**, and on
one: **Add a field to this one…** On Custom Fields: **Add a field…**, **Which forms
have we changed?** and **How does customizing work?**; on a form's Customize page: **Suggest changes to this
form**, **Add a field**, **What have we changed here?** and **How does
customizing work?**

## Under the hood

### What it is made of

| File | What it is |
|---|---|
| `extensions.py` | The Extension record's rules, and frappe's Client Script or Server Script made from it as Administrator. |
| `guard.py` | Pure. Reads an extension's code before it is kept and refuses what reaches past the administrator. |
| `places.py` | One's own pages an extension can run on (OneMail, OneCalendar, OneTask, OneCloud, OneIntake, the pipeline board, every space's home, a record's head): each one's events, what it gives, and what it may do. `../public/js/places.js` runs them. |
| `checks.py` | Pure. Whether an extension's code would work: the field and handler names it uses against the record's own, and its length. |
| `trial.py` | Tries an extension before it is kept: node parses screen code; server code runs once on a real record, undone after. |
| `review.py` | The second reading, `studio_review`: a separate call shown the code and its explanation, nothing of the chat. |
| `record_types.py` | A record type's rules, and frappe's custom DocType made, changed and deleted from it. |
| `doctype/workspace_field` | Custom Fields: a virtual doctype read from the workspace's ledger, frappe's own list. |
| `forms.py` | Each form's app and counts, for OneAI, and the extensions on one form. The Customize page is `page/customize` and `../public/js/customize.js`; what it saves is `../one/customize.py`. |
| `ai.py` | `write_extension`, `mend_extension`, `extensions_here`, `extension_code`, `extension_places`, `extension_mistakes`, `design_record_type`, `record_types_here`, on the `studio` action. |
| `mend.py` | An extension's errors, the Errors tab, and mending one from them (`studio_mend`). |
| `heads.py`, `notifications.py`, `legal.py` | The record heads; Extensions Failing and an extension turned on, off or deleted; and what the Terms and the AI Addendum say. |

### How it is made

**Code a workspace never writes.** frappe trusts whoever writes a script,
because only its own managers may. Here an administrator never writes one:
OneAI does, `guard.py` refuses what no explanation excuses (imports, raw SQL,
`get_all`, `db_set`, `ignore_permissions`, frappe's flags, mail, requests,
jobs, a kind or a field the administrator may not read; on the screen, the
server, the network, markup and the browser's storage), and a second model
reads it against its explanation. That second reading sees none of the
conversation, so whatever the administrator said to the writer does not
reach it. An administrator can still steer the writer, which is why the
guard and the review are the line, not the writer's instruction.

**Code nobody on the workspace reads.** The code is on the Extension at
permission level 1, which only frappe's System Manager reaches, so frappe
leaves it out of the form, the list and the API. `write_extension.unshown`
keeps it out of the chat as it is streamed and kept (`tools.shown_args`).
Changing one is writing it again from what it does. A screen extension's code
is sent to the browser that runs it, so it is not secret from somebody who
opens their browser's tools; it is only nobody's to change.

**On only as reviewed.** An extension turns on only if its review passed and
its code, record, view and event are the ones that passed
(`review.fingerprint`, `extensions.reviewed_as`): the guard and the reviewer
read the code for one kind of record at one moment. `read_only` keeps a field
only in the form, so `extensions.validate` keeps what OneAI wrote (`WRITTEN`)
on the server too: through the API as anywhere else, an administrator turns
an extension on and off and nothing more. A server one turns on only where the
bench runs server scripts (`server_script_enabled` in
`common_site_config.json`, set on our benches when they are made).

**Wrapped, on the server and on the screen.** frappe's Server Script is the
code inside `try`: `frappe.ValidationError` (a `frappe.throw`) passes,
anything else is logged under `OneStudio: <name>`, and the save goes on.
frappe's Client Script is the code given its own `frappe`
(`guard.WRAPPED_ON_SCREEN`), whose `ui.form.on` runs each handler inside a
`try` and whose `throw` is marked as meant: a meant throw still stops the
save, anything else is sent to `extensions.tripped` (rate-limited, only for an
extension that is on and on the screen) and logged under the same name.
`failing`, the Errors tab and the count on the extension cover both.

**On One's pages.** frappe has no script for a page of One's, so a page
extension (`view` Page, `place` such as `onemail.conversation`) is no Client
Script: the extensions that are on, and still as reviewed, come with the boot
(`extensions.boot`, `one_page_extensions`), and `places.js` runs each once,
keeping what it listens for with `one.on`. A page says what happened
(`onedesk.places.emit`) with a copy of what it shows and its own functions
for what places.py lets that event do; the extension is lent only those, its
handlers and any function it hands back run inside a `try`, and what trips is
sent to `extensions.tripped` under its name. `guard.on_page` refuses code that
listens for an event its page does not have. Screen code may look a record up
as the person (`guard.LOOKUPS`: `frappe.db.get_value`, `get_list`, `count`,
`exists`), and frappe answers with that person's permissions; anything else on
`frappe.db` is refused. Text passed to `__()` is words on the screen, never
read as the kind of record of that name. A space's home is frappe's own
Workspace page: `places.js` wraps `Workspace.show_page` rather than editing it,
and lends a spot above its blocks (`onedesk.places.spot`).

**On a schedule.** A scheduled extension (`event` Every Hour, Every Day, Every
Week, Every Month, or On a Schedule with `cron`, at most hourly by
`extensions.cron_refused`) is a Server Script of type Scheduler Event; frappe
makes its Scheduled Job Type, and stops it when the script goes. It runs as
Administrator with no `doc`, so `guard.on_server` refuses one that reads `doc`,
and its kinds are still held to what the administrator may open. Its wrapper
(`guard.WRAPPED_SCHEDULED`) logs an error under its name with no record.

**Checked before it is kept.** After the guard, `checks.py` (pure) reads the
code for what would not work: a field it names on `doc`, `frm.doc`,
`frm.set_value`, `toggle_*`, `set_df_property`, a lookup's fields and filters,
that the kind does not have (with the nearest that it does, by `difflib`); a
form handler frappe never calls; and code longer than `checks.LONGEST` lines.
`trial.py` then has node parse screen code (`node --check`, nothing run) and
runs server code once on the newest record of its kind the person may read,
inside a savepoint that is rolled back: an error refuses it, and what it did
(stopped the save with a message, changed these fields, nothing) is handed to
OneAI as `tried`. All of it comes before the review, so a refusal costs no
second reading, and goes back to the model as `mend`.

**Mending without reading.** `mend.py` is a separate call, its own action
(`studio_mend`), made on the server with the extension's code and its last
five errors (a server error's whole traceback, a screen error's message and
the browser's stack). It answers what went wrong in plain words and the code
mended; the code goes through `extensions.write` like anything OneAI writes,
and only the diagnosis comes back to the form or the chat. The button runs it
as a job (`mend.start`, two model calls are minutes, more than a request may
take) and tells whoever pressed it when it is done. Errors count from
`written_on`, when OneAI last wrote it: older ones are about other code. The Errors tab and
`extension_mistakes` show only the line of each error a person can read
(`mend.what_went_wrong`). A screen error carries the record it was open on.

**Record types are frappe's.** A custom DocType in module One Studio, made as
Administrator, with permissions written for the app's roles, and a place in
the app's rail through the sidebar layers `one/reports.py` already uses for
saved reports. Fields are frappe's own kinds, nothing that runs.

### The plan

Done: Extensions, the review, Custom Fields, Record Types. Not built: a child table in
a record type, a record type's own numbering (Numbering does it once it
exists), scheduled extensions (an Automation's schedule instead), and
extensions on API calls.
