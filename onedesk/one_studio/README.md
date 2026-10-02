# OneStudio

Written by hand. What OneStudio does and how to use it. Everything above
**Under the hood** is written for the people who use it, and OneAI reads it to
answer "how do I…" questions. Under the hood is for the people who build it.

OneStudio is where a workspace's administrators make One work the way their
business does: **Extensions** that make a form behave the way you need,
**Forms** to change what a form shows, and **Record Types** for the things
you keep that no app came with. You describe what you want to OneAI; it does
the making, and nothing changes until you approve it.

Only workspace administrators see OneStudio.

## Finding your way

**OneStudio** in the dock opens it. The rail has:

- **Extensions** — what OneAI has written for your workspace, on or off.
- **Forms** — every form you may change, the ones you have changed first.
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
the form: it can show, hide, fill in or require a field, and tell the person
something. On the **server**, it runs whenever the record is saved, submitted,
cancelled or deleted, whoever does it and however: the form, an import,
OneAI, another app. Use the server for a rule that must always hold.

**What you see, and what you do not.** Each extension opens on whether it is
**On** or **Off** (or **Refused by Review**, or **Cannot Run Here**) and what
it does, then when it runs, what was asked and by whom, and its review. You do
not see its code, and nobody in your workspace writes or changes it by hand,
so there is nothing to type and no Save: OneAI writes it, and to change one you
press **Change this one…** on it and say what ("make it apply only to new
customers"). OneAI writes it again, it is reviewed again, and it stays off
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

## Forms

**Forms** lists every form you may change. The ones your workspace has
changed, or has extensions on, come first, with how many; then every other
form, by the app it belongs to. Search by name. Open one to change it on the
**Customize** page: a field's label, whether it is hidden, required or in the
list, their order, fields of your own, and what the top of the form shows.
**Customize** in a form's own menu opens the same page.

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
away is hidden, never deleted, so nothing anybody entered is lost. **Forms**
changes how its form looks, as for any other form.

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

Nobody is told of their own change.

## Asking OneAI

On Extensions: **Write an extension…**, and **What do our extensions do?**,
which says what each does and whether any is failing. On an extension:
**Change this one…**; when it is on, **Has this one run into errors?**, which
reads what went wrong and on which record (never its code); when it is off,
**Why is this one off?** On Record Types: **Make a record type…**, and on
one: **Add a field to this one…**

## Under the hood

### What it is made of

| File | What it is |
|---|---|
| `extensions.py` | The Extension record's rules, and frappe's Client Script or Server Script made from it as Administrator. |
| `guard.py` | Pure. Reads an extension's code before it is kept and refuses what reaches past the administrator. |
| `review.py` | The second reading, `studio_review`: a separate call shown the code and its explanation, nothing of the chat. |
| `record_types.py` | A record type's rules, and frappe's custom DocType made, changed and deleted from it. |
| `forms.py` | The Forms list. The Customize page is `page/customize` and `../public/js/customize.js`. |
| `ai.py` | `write_extension`, `mend_extension`, `extensions_here`, `extension_mistakes`, `design_record_type`, `record_types_here`, on the `studio` action. |
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

Done: Extensions, the review, Forms, Record Types. Not built: a child table in
a record type, a record type's own numbering (Numbering does it once it
exists), scheduled extensions (an Automation's schedule instead), and
extensions on API calls.
