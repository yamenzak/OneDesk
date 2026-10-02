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

**What you see, and what you do not.** Each extension shows its title, what it
does, when it runs, what was asked and by whom, and its review. You do not
see its code, and nobody in your workspace writes or changes it by hand: OneAI
writes it, and to change one you ask OneAI ("make it apply only to new
customers"), which writes it again and has it reviewed again.

**Turning one on and off.** **Turn On** and **Turn Off** at the top of the
extension. One the review refused cannot be turned on; ask OneAI to change
it. Deleting an extension takes it away for good.

**When one goes wrong.** An extension on the server that runs into a mistake
does not stop anybody's work: the record still saves, the mistake is written
down, **Mistakes This Week** counts it, and every morning the administrators
hear of the extensions that ran into one. Ask OneAI to look at it and mend it,
or turn it off. A message an extension means to stop a save with, such as "A
customer needs a mobile number", is not a mistake: it stops the save, as it
says.

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

## Asking OneAI

On Extensions: **Write an extension…**, and **What do our extensions do?**,
which says what each does and whether any is failing. On an extension that is
off: **Why is this one off?** On Record Types: **Make a record type…**, and on
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
| `ai.py` | `write_extension`, `extensions_here`, `design_record_type`, `record_types_here`, on the `studio` action. |
| `heads.py`, `notifications.py`, `legal.py` | The record heads, Extensions Failing, and what the Terms and the AI Addendum say. |

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
its code is the code that passed (`review.fingerprint`), and a server one
only where the bench runs server scripts (`server_script_enabled` in
`common_site_config.json`, set on our benches when they are made).

**Wrapped on the server.** frappe's script is the code inside `try`:
`frappe.ValidationError` (a `frappe.throw`) passes, anything else is logged
under `OneStudio: <name>`, and the save goes on. `failing` counts those.

**Record types are frappe's.** A custom DocType in module One Studio, made as
Administrator, with permissions written for the app's roles, and a place in
the app's rail through the sidebar layers `one/reports.py` already uses for
saved reports. Fields are frappe's own kinds, nothing that runs.

### The plan

Done: Extensions, the review, Forms, Record Types. Not built: a child table in
a record type, a record type's own numbering (Numbering does it once it
exists), scheduled extensions (an Automation's schedule instead), and
extensions on API calls.
