# OneStudio

Written by hand. What OneStudio does and how to use it. Everything above
**Under the hood** is written for the people who use it, and OneAI reads it to
answer "how do I…" questions. Under the hood is for the people who build it.

OneStudio is where workspace administrators adapt One to their business.
Describe what you want to OneAI, and approve the card it makes. Nothing
changes before that.

Only workspace administrators see OneStudio.

## Finding your way

**OneStudio** in the dock opens it. The rail has:

- **Extensions**: scripts that make a form or page behave the way you need.
- **Custom Fields**: every field your workspace added or changed.
- **Custom Collections**: what your workspace keeps that no app came with.
- **Setup**: Numbering, Printing and Approvals, which open OneStudio's
  ControlCenter on that tab.
- **Automation**: Automations, Reports by Mail, Webhooks and Webhook Calls.

## Extensions

An extension makes a form do something it did not: refuse to save a customer
without a mobile number, fill in a field from another, warn when a discount is
over a limit, hide a field until another is ticked.

**Asking for one.** Click **Add Extension** and tell OneAI what you need, or
just say it in OneAI anywhere: "Stop an invoice being saved
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
  note under it. Only on the kind of record you name. One written for a
  Project runs on its page too.
- **A project's page**, when it is opened and each time the project changes:
  a note or a button under its header.
- **OneCalendar**, when an event's card is opened: show a note on it, or add
  a button.
- **OneTask**, each time a view of your tasks is shown: a note or a button
  under its name ("4 of your tasks are overdue").
- **OneCloud**, when a file is chosen: a note or a button under its preview.
- **Reading**, when a document is opened in the inbox: a note or a button
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
record has, every form event it uses must be one that forms really have, the
screen code must read as JavaScript, and it must be one change, not a hundred
lines of them. Code for the server is also run once on one of your records and
undone straight away, so an error shows now rather than on someone's next
save, and OneAI is told what it did ("it stopped the save, saying…"). Whatever
is wrong goes back to OneAI, which mends it before anything reaches you.

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
outside your workspace (no mail, no calls to other services); change the
system's own records or One's; run more often than once an hour. OneAI says
so when what you ask needs one of these, and offers what it can do. For
something that tells people, an **Automation** is the way.

**Server extensions** run only on workspaces where they are turned on. If an
extension says **Cannot Run Here**, ask us.

## Custom Fields

**Custom Fields** lists every field your workspace added to a form or changed
on it: the field, its form, its type, and the other forms it was also added
to. **Added** marks a field the workspace made, **Changed** a standard field
it changed. Filter by form, status or app, or search by name. **Custom
Fields** on a form's own menu opens the list filtered to that form.

- **Add a field**: click **Add Field** and tell OneAI what you need. It asks a
  few questions, recommends the field type and properties, suggests related
  forms that need the field too (for example Item fields on invoice and order
  items), and makes one card to approve.
- **Change a field**: click it. OneAI asks what to change.
- **Export or Reset**: tick fields, then choose from **Actions**. Reset
  removes everything the workspace changed on those forms.
- **Restore a field**: a removed field is in One › **Recycle Bin**. Restoring
  it brings back its values too.

See Customizing a Form in One's documentation.

**Who sees and changes it.** Workspace administrators only, on the forms they
can open, and never the framework's own forms or One's. A change applies to
everyone who opens the form. The other administrators are notified
(**Form Customized**).

**OneAI** on the list says which forms were changed and how, or changes the
one you name. On a form it adds a field step by step, suggests changes as one
card, says what was changed and which extensions run on it, or explains how
customizing works. A check no field setting can say, it offers as an
extension.

## Custom Collections

A custom collection is something your workspace keeps that no app came with:
memberships, vehicles, rooms, contracts, inspections.

**Adding one.** Click **Add Collection** and tell OneAI what you keep, for
example "the vans we keep: registration, make, mileage, the date we bought it
and whether it is in use." OneAI designs its fields and shows a card with its
name, app and fields. **Approve** creates it.

**Where it is.** In the rail of the app it belongs to, in the group you choose:
one the rail already has, such as **Sales** in OneCRM, or a new one. Without a
choice it goes under **Your Records**. People who use that app create and edit
its records, and its managers delete them. A collection in **One** is for
everyone.

**Moving one.** Tick it and click **Actions › Move**, then choose the app and
the group. Its records stay as they are, and the people who use them follow
the app.

**Opening one** opens its records.

**Field types.** Text, numbers, money, percentages, dates and times, checks,
selects, phone numbers, ratings, durations, files and images, and links to
records you can open or to another collection. The first text field is each
record's title.

**Numbering.** Each record gets a number from the collection's initials, such
as CV-00001 for a Company Van. Change it in Setup › **Numbering**.

**Changing one.** Tick it and click **Actions › Change**, or ask OneAI, for
example "Add a colour to Company Van." A removed field is hidden, not deleted, so no
data is lost.

**Deleting one.** Delete its records first. A collection that still has
records can't be deleted. A deleted collection is in One › **Recycle Bin**, and
restoring it brings back its records list.

## Notifications

Every administrator is notified in One and by email, unless they turned it
off in their notifications:

- **Extensions Failing**: each morning, the extensions that hit an error the
  day before. Not sent when none did.
- **Extension Turned On**: when another administrator turns one on, with what
  it does and where it runs.
- **Extension Turned Off** and **Extension Deleted**: in One only, unless you
  turn on email.
- **Collection Added**: when another administrator adds a custom collection,
  with its fields and where its records are.
- **Collection Changed** and **Collection Deleted**: in One only, unless you
  turn on email.
- **Form Customized**: when another administrator changes a form or resets
  it, in One only unless you turn on email.
- **Extension Fixed**: when Fix With OneAI has mended an extension, to
  whoever asked.

No one is notified of their own change.

## Asking OneAI

On Extensions: **Write an extension…**, and **What do our extensions do?**,
which says what each does and whether any is failing. On an extension:
**Change this one…**; when it is on, **Has this one run into errors?**, which
reads what went wrong and on which record (never its code); when it is off,
**Why is this one off?** On Custom Collections: **Make a collection…** and
**Change a collection…**; on one collection, **Make a collection…** On
Custom Fields: **Add a field…**, **Which forms
have we changed?** and **How does customizing work?**

## Connections

- **From OneAI**: Extensions, custom fields and custom collections come from cards OneAI makes. Nothing changes until an administrator approves the card.
- **To One**: An extension can add a button or a note to a record's head and to every space's home. A custom collection is listed in its app's rail, and a deleted one goes to the Recycle Bin.
- **To OneMail**: An extension can add a note or a button to a conversation. It can also fill in a new message's subject, cc or bcc.
- **To OneCRM**: An extension can add a note above the pipeline board.
- **To OneProject**: An extension can add a note or a button under a project's header.
- **To OneCalendar**: An extension can add a note or a button to an event's card.
- **To OneTask**: An extension can add a note or a button under a view's name in My Tasks.
- **To OneCloud**: An extension can add a note or a button under a file's preview.
- **To OneAI**: An extension can add a note or a button under a document's head in the Intake inbox.

## Under the hood

### What it is made of

| File | What it is |
|---|---|
| `extensions.py` | The Extension record's rules, and frappe's Client Script or Server Script made from it as Administrator. |
| `guard.py` | Pure. Reads an extension's code before it is kept and refuses what reaches past the administrator. |
| `places.py` | One's own pages an extension can run on (OneMail, OneCalendar, OneTask, OneCloud, OneAI, the pipeline board, a project's page, every space's home, a record's head): each one's events, what it gives, and what it may do. `../public/js/places.js` runs them. |
| `checks.py` | Pure. Whether an extension's code would work: the field and handler names it uses against the record's own, and its length. |
| `trial.py` | Tries an extension before it is kept: node parses screen code; server code runs once on a real record, undone after. |
| `review.py` | The second reading, `studio_review`: a separate call shown the code and its explanation, nothing of the chat. |
| `record_types.py` | A record type's rules, and frappe's custom DocType made, changed and deleted from it. |
| `doctype/workspace_field` | Custom Fields: a virtual doctype read from the workspace's ledger, frappe's own list. |
| `forms.py` | Each form's app and counts, and the extensions on one form, for OneAI. What OneAI's card saves is `../one_studio/customize.py`. |
| `ai.py` | `write_extension`, `mend_extension`, `extensions_here`, `extension_code`, `extension_places`, `extension_mistakes`, `design_record_type`, `record_types_here`, on the `studio` action. |
| `mend.py` | An extension's errors, the Errors tab, and mending one from them (`studio_mend`). |
| `heads.py`, `legal.py` | The record heads, and what the Terms and the AI Addendum say. Extensions Failing and an extension turned on, off or deleted are in `notifications/one_studio/`. |
| `tell.py` | Every notification OneStudio sends: an extension turned on, off or deleted, the ones failing, and a collection added, changed or deleted. |

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
Week, Every Month, or Scheduled with `cron`, at most hourly by
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
the app's rail through the sidebar layers `one_studio/reports.py` already uses for
saved reports. Fields are frappe's own kinds, nothing that runs.

### The plan

Done: Extensions, the review, Custom Fields, Custom Collections. Not built: a child table in
a record type, and extensions on API calls (`docs/BACKLOG.md`).

### ai.py

- `extensions_here` reads what the workspace has: each extension, where and
  when it runs, whether it is on, its review, and whether it ran into a
  error lately. No code.
- `write_extension` keeps what OneAI wrote, off, after the guard and the
  review (`extensions.write`), and makes a card whose Turn On does what the
  administrator would do in the list. A refused review comes back to the
  model to mend, under the same extension. The code it wrote is left out of
  the conversation as it is kept and shown (`unshown`), so it is in the
  extension alone.
- `extension_code` hands OneAI the code it is changing, so a change edits it
  rather than rewriting it from the explanation. Its answer's code is
  `unshown` too: the run reads it, the kept conversation does not.

Both run on OneStudio Extensions (`studio`), a stronger model than the
chat's, which is told what an extension may do.

### checks.py

`guard.py` says what an extension may do; this says whether what it does is
there. A model writing frappe code invents a field name, or names a handler
frappe never calls, and the code passes every review and then does nothing,
or runs into an error on every save. So the names the code uses are read
against the record's own fields, and what is wrong comes back to OneAI in
words it can mend from, with the fields that are there.

### extensions.py

An extension is one record of ours, **Extension**, and one of frappe's: a
Client Script for one that runs on the screen, a Server Script on a record
event for one that runs on the server. Ours holds what the administrator
reads (the title, what it does, what was asked and the review) and, at a
level only frappe's System Manager reads, the code; frappe's is made from it
here, as Administrator, since frappe keeps both to its own managers, and is
nobody else's to change.

- **Written only by OneAI** (`write`, called by its tool in `ai.py`), after
  `guard.py` has read the code and `review.py` has had a second model read it
  against what it says it does. Nothing it writes is on until somebody turns
  it on.
- **On only as reviewed.** An extension turns on only if its review passed
  and its code, record, view and event are the ones that passed
  (`reviewed_as`). Nothing OneAI wrote changes by hand (`WRITTEN`). One on the
  server turns on only where the bench runs server scripts at all.
- **Off and deleted by the administrator.** Off disables frappe's script;
  deleting the extension deletes it.
- **An error does not stop the work.** Every extension runs wrapped
  (`guard.wrapped` on the server, `guard.wrapped_on_screen` in the browser):
  what it means to stop a save with still stops it, and anything else it
  trips on is written to the error log under its name (in the browser through
  `tripped`) and the work goes on. `failing` tells the administrators each
  morning.

Who hears of an extension turned on, off or deleted, and of the ones failing,
is `tell.py`.

### guard.py

An extension is code OneAI writes, and nobody else. An administrator could
still ask OneAI for code that reaches past what they may do, so this reads
the code itself, as a second line after the review (`review.py`), and refuses
what no explanation would excuse.

**On the server** an extension is a Server Script on a record event, run in
frappe's sandbox as whoever saved the record. The sandbox already refuses
imports, files and the private parts of objects; this refuses the rest of
what it leaves open:

- writing past permissions: `db_set`, `db.set_value`, `ignore_permissions`,
  frappe's flags, deleting or renaming another record;
- reading past them: raw SQL, `get_all` (frappe's `get_list` checks), a
  password, and any field the administrator may not read;
- reaching outside: requests, mail, jobs, other scripts and whitelisted
  methods;
- naming a kind of record they cannot open, or frappe's or One's own, and
  naming one any way but as plain text, so every kind it touches is known.

**On the screen** an extension is a Client Script, which runs in the browser
of everybody who opens the form. It may change the form and speak to the
person; it may not call the server, store or send anything, or write markup.

`IN_THE_SANDBOX`, the names a server extension's code finds already there, is
frappe's safe_exec globals and RestrictedPython's builtins, as
`get_safe_globals()` answered on frappe develop (Oct 2026), and `print`, which
RestrictedPython turns into its own collector.

`WRAPPED_ON_SCREEN`: each handler a screen extension gives
`frappe.ui.form.on` runs inside a `try`, a `frappe.throw` it means still stops
the save, and anything else it trips on is written down
(`extensions.tripped`) and the form goes on. Its `frappe` is frappe's own,
with those two wrapped; everything else is frappe's.

### mend.py

An administrator never reads an extension's code, so they cannot read why it
fails either: the errors frappe keeps are about the code, line by line. So the
mending is a separate call, its own AI action (`studio_mend`), made here on
the server: shown where the extension runs, what it says it does, its code
and its last errors, and asked what went wrong, in words for somebody who
does not read code, and for the code mended. Nothing of the chat reaches it,
and nothing it is shown goes back to the chat: the conversation, and the
extension's form, hear the diagnosis and nothing else.

What it writes goes through `extensions.write` like anything OneAI writes:
the guard, the second reading, kept off. The mended version runs only once an
administrator turns it on.

### places.py

A frappe Client Script reaches a kind of record's form and its list, and
nothing else: OneMail, OneCalendar, OneTask, OneCloud, OneAI, the pipeline
board, a project's page, every space's home and the head of a record (on its
form, and on a project's page) are One's own, drawn by One's code. So each of
those says here, once, what happens on it that an extension may hear (its
events), what each event tells the extension (`gives`), and the few things
the extension may do there (`may`).

This is the whole contract. The browser runs only these events with only
these powers (`public/js/places.js`); `guard.py` refuses code that listens for
an event the page does not have; and OneAI reads it to know what each page
allows (`ai.py` `extension_places`), so what it writes and what runs are the
same list.

### record_types.py

A record type is frappe's own custom DocType (`custom`, module One Studio),
with a **Record Type** of ours beside it that the administrator reads: what
it is for, the app it belongs to, who asked. OneAI designs one from what was
asked (`ai.py`), and approving the card makes it here, as Administrator, since
frappe makes DocTypes for its own managers alone.

What a workspace's record type may be, whoever asks:

- plain fields of the kinds a form is made of (`FIELDTYPES`): text, numbers,
  money, dates, ticks, choices, files, and links to a kind of record the
  administrator may open, or to another record type. Nothing that runs:
  no code, no HTML block, no button, no condition on another field;
- a name that is not taken, by frappe, an app, or another record type;
- belonging to one app: its users make and change records of it, its
  managers delete them, and it is listed in that app's rail, in the group
  the administrator chose (one the rail has, or a new one), else under Your
  Records. One is everybody's.

Each record is numbered from the collection's initials, CV-00001 for a
Company Van, as the workspace's documents are, so the number a person sees
beside its title means something; Workspace > Numbering changes it.

Changing one adds fields, renames them and changes their choices; a field
already holding data is never dropped, only hidden. Deleting one deletes its
records, so it is refused while it has any.

Who hears of a collection added, changed or deleted is `tell.py`.

### review.py

OneAI writes an extension from what an administrator asked, so whoever asks
steers the writer. The reviewer is a separate call, its own AI action
(`studio_review`), shown the code, the explanation the administrator will
read, and where it runs, and nothing of the conversation, so nothing said
there reaches it. It answers Pass or Refuse with a reason. `guard.py` has
already refused what no explanation could excuse; this catches code that is
allowed but is not what it says: a check that also copies a field elsewhere,
a button that does more than its label.

An extension that has not passed, or whose code, record, view or event has
changed since it passed, cannot be turned on (`extensions.py`).

### trial.py

- **Screen code is parsed** by node (`node --check`), which reads it and
  runs nothing: a missing bracket comes back with its line, rather than as a
  form that silently has no extension. Where the bench has no node, nothing
  is said.
- **Server code is run once on a real record** of its kind, the newest the
  person may read, inside a savepoint that is rolled back: whatever it
  changed or made is undone. A scheduled one is run once as it will run,
  with no record, and undone the same way. What happened comes back to OneAI
  as it would on that record: it stopped the save with this message, it
  changed these fields, or it ran into this error, which refuses it.

Both come after `guard.py` and `checks.py`, so what is tried has already been
read for what it may do and for the names it uses.
