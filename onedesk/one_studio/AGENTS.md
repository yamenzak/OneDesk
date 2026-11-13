# OneStudio

The one file for agents, OneAI and us: what OneStudio is made of, its rules,
where each file is, and the decisions that cost something. What people read
is in `docs/`, one page per thing they do, shown in Help and searched by
OneAI's `how_to`; its versions are `docs/changelog/`. What is known to be
wrong and what is planned is `SCRATCHPAD.md` (docs/READY.md, A module's
folder).

OneStudio is where workspace administrators adapt One to their business:
extensions, custom fields, custom collections, numbering, printing,
approvals, automations, reports by mail, dashboards and webhooks. They
describe what they want to OneAI and approve the card it makes; nothing
changes before that. Read this file before touching scripts, DocTypes or
what OneAI may write.

**No roles of its own.** OneStudio is for the workspace's administrators,
whose role (Workspace Administrator) is One's (`one/roles.py`), so it ships
no `abilities.py`; the manifest's `no_roles` says so. Its records give that
role and frappe's System Manager their permissions in their own JSON.

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
| `places.py` | One's own pages an extension can run on (OneMail, OneCalendar, OneTask, OneCloud, OneAI, the pipeline board, a project's page, every space's home, a record's head): each one's events, what it gives, and what it may do. `../public/js/one_studio/places.js` runs them. |
| `checks.py` | Pure. Whether an extension's code would work: the field and handler names it uses against the record's own, and its length. |
| `trial.py` | Tries an extension before it is kept: node parses screen code; server code runs once on a real record, undone after. |
| `review.py` | The second reading, `studio_review`: a separate call shown the code and its explanation, nothing of the chat. |
| `record_types.py` | A record type's rules, and frappe's custom DocType made, changed and deleted from it. |
| `doctype/workspace_field` | Custom Fields: a virtual doctype read from the workspace's ledger, frappe's own list. |
| `forms.py` | Each form's app and counts, and the extensions on one form, for OneAI. What OneAI's card saves is `../one_studio/customize.py`. |
| `ai.py` | `write_extension`, `mend_extension`, `extensions_here`, `extension_code`, `extension_places`, `extension_mistakes`, `design_record_type`, `record_types_here`, on the `studio` action, and in `NOT_FOR_AI` why each call that changes something is reached by another card or by no card. |
| `mend.py` | An extension's errors, the Errors tab, and mending one from them (`studio_mend`). |
| `heads.py`, `legal.py` | The record heads, and what the Terms and the AI Addendum say. |
| `tell.py`, `notifications.py` | Every notification OneStudio sends, and what each says: an extension turned on, off, deleted or fixed, the ones failing, a collection added, changed or deleted, and a form customized. |
| `setup.py`, `tour.py` | No setup steps of its own, and the tour of its rail. |
| `manifest.py` | Its place in One, its Help pages in reading order, and why it ships no roles. |

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
these powers (`public/js/one_studio/places.js`); `guard.py` refuses code that listens for
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

### ai_setup.py

Each tool in ai_setup.py checks what it was asked against the same rules the
page does, and writes a card (an `AI Proposal` of kind Setup) that does
nothing until a person approves it. Approving runs the page's own code
(one_studio/reports.py, one/access.py) as whoever pressed Approve, so a card can do
no more than they could by hand. A card says in plain words what changes: a
level's card names every right it gives and takes away.

All of them run on Workspace Setup, the stronger model approvals and
automations run on.

### approvals.py

An approval is frappe's own Workflow: its states, the actions between them,
and the role each action is for, drawn in frappe's workflow builder. The
workspace administrator is given Workflow, Workflow State and Workflow
Action Master, and the builder page through frappe's Custom Role.

Frappe trusts whoever writes a Workflow, because only its System Managers
may, and a workflow can run code: a transition's condition is Python, a
state's value can be an expression, a transition can run tasks (a Server
Script's method among them), and the field the workflow keeps its state in is
written on every record of the kind. A workflow written by somebody frappe
does not let customize (layer.held) is held to this:

- it is on a kind of record they can open, never frappe's own or One's;
- its transitions run no tasks, and a condition only compares the record's
  own fields with plain values (`doc.grand_total > 5000`), so a bill over a
  sum can go to a manager without a line of code;
- a state sets a field only to a plain value, and only a field anybody who
  may edit the record may set (the first permission level, not the record's
  own bookkeeping);
- it keeps its state in a field of its own, which is made here the first
  time, as frappe makes it but as the workspace, since the administrator may
  not add a field by hand.

Every approval, the workspace's or not, is told through One's hub: frappe's
own mail to whoever a step waits on is off (`send_email_alert`), and
`waiting` tells them on the bell, and by mail as they chose, as Approval
Waiting. One made without the builder (by OneAI, or by code) is laid out for
it, since frappe's builder stacks every step it has no place for on one spot.

### automation_steps.py

Tell People tells people through the hub (one/notify.py), on the bell and by
mail as each chose, as Automation Notice, and fills a mail template in as the
composer does (one_mail/mail_templates.py). Frappe's Send Notification mails past
the hub, and renders a template with only `doc`, so a template that names the
record's fields bare, as the composer and the leave mails need, prints its
tags there.

### automations.py

An automation is frappe's own Automation Flow: a trigger, the records it
matches, and steps (set a field, make a record, notify, assign, call a
webhook, wait). The workspace administrator is given Automation Flow, and
it is listed in One's sidebar, so its list and form keep One's rail.

Frappe trusts whoever writes a flow, because only its System Managers may.
A flow runs as Administrator unless told otherwise, its condition and an If
step's are Python, every step's values are Jinja with frappe's globals, and
a step can run a Server Script. A flow written by somebody frappe does not
let customize (layer.held) is held to this:

- it runs as whoever wrote it, so each step can do only what they could do
  by hand, and frappe's own permission checks decide;
- it decides by its field rules, never by code: no condition, no If step;
- it runs no script;
- a value names a field of a record, `{{ doc.customer_name }}`, and nothing
  else (as one_mail/mail_templates.py holds a template);
- a webhook is sent over https (frappe already refuses internal addresses);
- it is on a kind of record they can open, never frappe's own or One's.

Automation Settings stays the operator's.

**Tell People** (`TellPeople`, one_studio/automation_steps.py) is One's own step,
added through frappe's `automation_actions` hook: it tells people through the
hub (one/notify.py), on the bell and by mail as each chose, as Automation
Notice, and fills a mail template in as the composer does
(one_mail/mail_templates.py), from the record's own fields. Frappe's Send
Notification mails past the hub and renders a template with only `doc`, so a
template named by its fields prints its tags; it is not offered to a
workspace's own flows.

### customize.py

What a workspace administrator changes on the Customize page is frappe's own
records, and one of ours:

- **Fields**: a field's label, whether it is hidden, required or in the list,
  and the order of them all, as **Property Setters**; a field of the
  workspace's own, as a **Custom Field**, which it may change again or take
  away. A field the record came with may be hidden, never removed.
- **Above the fields**: rows of the doctype's **Record Head** (one/head.py):
  numbers in the band, verbs a module registered, and linked sections
  (one/linked.py). A module's own rows are shown and kept; the workspace's are
  marked `custom`, so a migrate keeps them too.
- **Connections and buttons**: the DocType's own Links and Actions, marked
  `custom` as frappe's Customize Form marks them. A button there only goes
  somewhere; one that runs something is a verb.

Every row is written under `frappe.flags.one_workspace_layer`, so the holds in
one/layer.py read it as the workspace's, and it is saved against the state
the page loaded (`state`), so two administrators do not overwrite each other.
What frappe does not mark (a custom field, a property setter) the page writes
into a ledger, **Workspace Customization**, and **Reset** takes back what the
ledger names and nothing else: a module's customizations are never the
workspace's to remove.

### letter_heads.py

frappe keeps a letter head's top as HTML, and ERPNext's own reads the
company's logo, name, address and contacts from the document as it prints. A
workspace's letter head may hold no template (`print_html.letter_head_html`),
so its top is drawn in letter_heads.py instead: one of `PRESETS`, from what
Workspace > General keeps (the logo, the name, the company's own address, its
phone, email, website and tax ID, and its Brand Colour), showing what the
administrator ticked. The choice is kept on the letter head (`one_top`), and
the top is drawn again whenever the company or its address changes (`redraw`),
so a printed page always says what General says now.

The foot is drawn the same way, from `FEET` (`one_foot`, `draw_foot`). It
carries no page number: that is the print format's own (Print Format's Page
Number), which frappe draws on every page.

A top or foot written by hand, in frappe's builder, stays as it was written:
editing a drawn one there makes it hand-written (`apply`).

In `draw`, the logo's cell is as wide as the logo, so the company's lines have
the rest of the width and the address and the contacts each stay one line. It
is said in pixels: frappe's print style holds every letter head picture to its
cell, and a cell sized to its content would hold it to nothing.

### numbering.py

Frappe keeps this in Document Naming Settings, a Single whose whitelisted
methods change any doctype's series and run for anybody who can read it
(`run_doc_method` checks read, and `update_series` writes the property
setters itself). So the workspace administrator is not given that Single.
numbering.py's functions are the doors instead, each guarded to a doctype the
workspace may change and its administrator may read, and each calling
frappe's own logic: `update_series` validates a series and refuses one
another doctype uses, `NamingSeries` previews and counts.

The one thing frappe lets its System Managers do that numbering.py does not:
set a series' next number lower. Going down repeats a number already used, and
the save that meets it fails; going up only skips numbers, as a new year does.

`NAMED_BY` holds the kinds of record that name themselves in code, by one of
their app's own settings: the Single, the field, the method that shows or
hides the series and the name field to match (or None), and whether the code
reads the setting as a global default, which the Single's save would have
written.

`SERIES`, `FIELD` and `EXPRESSION` are how any other kind may be named, as
frappe's Customize Form offers it: the naming rule it records, and what it
writes as `autoname`. Frappe's Autoincrement cannot be changed to or from once
records exist, UUID changes how the name is stored, and By script is code, so
none is offered.

### print_blocks.py

Everything One submits prints from a format laid out in frappe's print format
builder (each module's `print_format/`, written by `scripts/print_formats.py`)
out of the builder's own pieces: fields, tables, linked fields, static text,
sections that show only when they say something. A workspace changes them in
the builder like any of its own.

A few papers are gathered from records the one printed doesn't hold, which the
builder can't reach. That part alone is one of One's blocks, frappe's own Print
Format Field Templates, standard in module One
(`one/print_format_field_template/`), so a workspace finds them in the
builder's Library; the rest of the paper is still the builder's:

- **One Statement**: a customer's or a supplier's account this fiscal year,
  from the general ledger: the opening balance, each document with the
  balance after it, how old what's open is, the open invoices, and where to
  pay. On **One Statement of Account** and **One Supplier Statement**.
- **One Salary Certificate** and **One Experience Letter**: the letter an
  employee asks for, dated today, with the monthly pay as their latest
  payslip made it up.
- **One Leave Balance**: each leave the employee has, on a leave
  application, as HRMS counts it.
- **One Total**: a payment order's total, which it doesn't keep.
- **One Progress**, with **One Title**, **One Party** and **One Details**:
  a project's status, the one paper still drawn wholly from blocks.

Each template (templates/one_print/) is drawn from `one_print_block`, which
says what to show; every amount is frappe's own formatting in the record's
currency.

Each record in `FORMATS` prints with One's format unless the workspace has
chosen another (`settle`), and ERPNext's own that One's replace (`REPLACES`)
are turned off.

### print_html.py

A printed page is drawn on this site's address, where a script runs as
whoever opens it, and a PDF is drawn by a browser on the server, which fetches
whatever the page points at. And an HTML block is a Jinja template, which
frappe renders with globals that read any table (`frappe.db.sql`,
`frappe.get_all`) and fetch any address (`make_get_request`). So what a
workspace administrator writes in HTML is held to three things:

- **The template reads the record and nothing else** (`check_template`): the
  record's fields and rows (`doc.grand_total`, `{% for row in doc.items %}`),
  `doc.get_formatted(...)` and `doc.get(...)`, conditions, loops, arithmetic,
  `_()` and plain filters. It is rendered in a sandbox of its own that holds
  only those (`render`), escaping every value, never in frappe's.
- **The markup is markup for paper** (`clean`): text, headings, tables, lists,
  images and links, with scripts, forms, frames, media and event handlers
  taken out.
- **Nothing is fetched from elsewhere**: an image is this site's file or an
  inline image, and a style may not import or point off this site.

A block the workspace saves is marked `one_sandboxed`, and onedesk's copy of
frappe's HTML block macro (templates/print_format/macros/HTML.html) renders a
marked block through `render`. A block frappe or its System Managers wrote is
unmarked and renders as frappe renders it. A letter head's HTML is rendered by
frappe as it is stored (printview.get_letter_head), so it holds no template at
all and is stored already cleaned.

### print_props.py

The properties are read from frappe's builder (public/js/print_format_builder:
field_properties.js, SectionPropertiesPanel.vue, TableFieldInspector.vue,
BarcodeRows.vue and the rest of the inspector) and checked against what its
renderer reads (templates/print_format/print_format.html, macros.html and
macros/*): a property the builder sets and the page never reads is left out,
and so is one the page reads that nothing sets. What each accepts is what the
builder's own control offers.

A value is checked in print_props.py for its shape; a style for what it may
load (`printing._style`), and a condition for its grammar. frappe runs a
condition in its own safe_eval with the record and the print settings, as the
builder's own do.

### print_recipes.py

OneAI designs a print format as the builder lays one out
(`ai.design_print_format`). Left to itself, two requests for the same invoice
came out as two different pages. So `print_layout` offers a starting layout
made from the kind's own fields, in the order a reader looks for them, and
OneAI changes only what was asked. The look is frappe's own print style with
`HOUSE_CSS` over it: the same page, spaced and toned the way frappe-ui draws
one, so it still reads like every other format the workspace prints. A format
made to a look somebody asked for carries their css instead, never this one as
well.

Two shapes cover what a workspace prints:

- a document of trade (an invoice, a quotation, an order, a delivery note, a
  bill): who it is for and where on the left, its dates and references on the
  right, the items as one table, the amount in words beside the totals, and the
  terms last;
- anything else: its main fields in two columns, each of its tables with the
  columns its list shows, and its long text last, each under its label.

Every layout is written as `ai.LAYOUT_HELP` describes: sections of columns of
blocks.

`HOUSE_CSS` is the house finish over frappe's print style, in frappe's own
classes and its grey scale: labels small and muted, room between sections,
tables lined rather than boxed under a soft header, the totals as label and
figure on one line and the grand total set off above them. Sizes are em, as
frappe's are.

### printing.py

The formats are frappe's own: Print Format made in frappe's print format
builder, and Letter Head. The workspace administrator is given both, and the
builder page, through frappe's own Custom DocPerm and Custom Role. What is
held in printing.py is what a printed page may carry when somebody frappe does
not let customize wrote it (layer.held), because the page is drawn on this
site's origin, where a script runs as whoever opens it, and a PDF is drawn by
a browser on the server:

- **A format is made in the builder.** No hand-written HTML format, no raw
  printing, no JS format, and in the builder no Typst block, which reads
  files. An HTML block is allowed as print_html.py holds it: a template that
  reads only the record, rendered in a sandbox of its own, its markup cleaned.
  Everything else the builder offers (fields, tables, text, images, barcodes,
  a standard field template) is escaped by frappe's own macros.
- **Styles are styles.** A format's CSS goes into a `<style>` element as it
  is, so it may not contain markup, `@import`, or a URL that is not this
  site's file or an inline image; a block's own style, likewise.
- **A letter head is a picture or plain HTML.** Its top and foot are each a
  picture, which frappe turns into its own markup, or HTML with no template in
  it, stored cleaned (`print_html.letter_head_html`). The header and footer
  scripts stay frappe's System Managers'.

A standard format stays frappe's (it refuses changes outside developer
mode); a workspace copies it in the builder and changes the copy.

`DESIGNER` is the workspace's own format frappe's builder opens to design a
letter head on: the builder draws a format's letter head above and below it,
top and foot, each a picture or HTML. It is kept off, so nothing prints with
it, and out of every list of formats.

### reports.py

Three things, each frappe's own:

- **Saved reports.** A list's Report view, saved under a name, is frappe's
  `Report` of type Report Builder. Anybody may save one (frappe offers Save As
  to everybody, and its `save_report` only ever writes that type), and it goes
  in the sidebar of the app whose list it was: for everybody when a workspace
  administrator saved it, in the person's own sidebar otherwise, through
  frappe's own sidebar layers (`Custom Sidebar`). Deleted, it leaves.
- **Dashboards.** frappe's `Dashboard`, of its `Dashboard Chart` and `Number
  Card`, which a workspace administrator makes. Everybody sees them under One >
  Dashboards, and frappe shows each chart only to who may read what it counts.
- **Reports by mail.** frappe's `Auto Email Report`, which a workspace
  administrator sets from a report's menu (Setup Auto Email).

What frappe trusts to whoever may customize it, and a workspace does not get:

- a report of any type but Report Builder. A Custom Report runs the report it
  is a copy of with no check of who may open that one, and frappe leaves
  Script and Query reports to its Script Manager already;
- a chart or a card of type Custom, which runs code an app wrote and is free
  to read past the reader's permissions;
- a report by mail that runs as somebody else.

erpnext's own dashboards are its modules' (Accounts, Stock, CRM), with a
company on every chart, each on its own app's rail. OneStudio › Dashboards
is where a workspace makes and changes them.
