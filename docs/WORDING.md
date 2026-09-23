# How a field is worded

Every label and every description this app adds is read next to frappe's and
hrms's own. If ours sound different, the form reads as two products. This is
the house style, taken from frappe's own JSON rather than invented: the samples
below are all real, from `frappe/automation`, `frappe/core` and
`frappe/website`.

## The label

**Title Case, a noun phrase or a verb phrase — never a sentence about people.**

    Enable Scheduled Jobs
    Minimum Password Score
    Allow Login using Mobile Number
    Prevent self approval for leaves even if user has permissions
    Delete Background Exported Reports After (Hours)

A Check starts with the verb the operator is performing — `Allow`, `Enable`,
`Send`, `Show`, `Prevent`, `Restrict`, `Require`, `Auto` — or is a bare noun
when the section already supplies the verb (`Holidays`, `Birthdays`,
`Work Anniversaries` under **Reminders**).

**Units go in the label, in brackets.** `Attachment Limit (MB)`,
`Retirement Age (In Years)`, `Report Timeout (In Seconds)`. Never left to the
description to explain.

**Other doctypes are named exactly**, in Title Case, so the reader can go and
look at one.

## The description

**Most fields do not get one.** hrms's own HR Settings has forty-odd fields and
four descriptions. A description is for what the label cannot carry: the unit,
the limit, the consequence, the dependency. If it only restates the label,
delete it.

**When there is one, it is one sentence.** Two when the second states what
happens at the boundary, or the cost:

    Stop dispatching automations site-wide. Queued rows are left untouched.
    Bytes of output a step may publish to later steps. Larger output is dropped, not failed.
    When sending document using email, store the PDF on Communication. Warning: This can increase your storage usage.

**The openers frappe uses**, and there is no reason to invent others:

    If enabled, …            If unchecked, …         When enabled, …
    Allow …                  How many … before …     Number of days after which …
    Defaults to `…`          Leave empty to …        Set to 0 to …
    Requires …               Example: …              Only …

**It says what the system does, not why that is a good idea.** The reason lives
in the module README, in `docs/`, or in a docstring — never in a description a
person reads while ticking a box.

## What is out

No metaphor, no anecdote, no rhetorical contrast. All three of these were in
this app and are gone:

    A router reboot stops locking everybody out on a Monday.
    A system that locks a plumber out at a customer's door is a system they stop using.
    A live frame from the camera, never a file. Says who, not where.

No second person plural about the workforce ("Employees may clock themselves
in"), no wink at the reader, no sentence that is there because it reads well.
The test is whether the line would look out of place two rows above
`Allow Login using Mobile Number`.

## The two pages a customer reads

`/start` and `/welcome` are the only screens somebody reads before they have a
workspace, and the rules above still hold — Title Case labels, one sentence of
help, nothing that restates the label. Two things are different.

**Say what happens, not who is doing it.** "Payment received. The workspace is
being built" rather than "Thank you. We are building your workspace." The first
person is a voice the rest of the product does not have, and on a page that is
mostly about money it reads as reassurance rather than fact.

**A consequence is stated once, where the choice is.** The jurisdiction radio
carries "This cannot be changed later. Files stay where the workspace was
built", because that is the field it is true of. It is not repeated on the
plan, on the button, or on the page that follows.

## The guard

`tests/test_wording.py` holds every doctype and every custom field in the app
to what can be checked by machine: a description of at most 130 characters and
two sentences, with no first person, no em dash and no colon except after
`Example`; a label in Title Case with no full stop, at most 60 characters, that
is a name rather than a sentence ("What It Reads" was a label here). The rest of
this page — no reasoning, frappe's openers, most fields with no description at
all — is still read by a person.

## Translation

Every label, description, Select option and `_()` string is extracted into
`onedesk/locale/main.pot` by `bench generate-pot-file --app onedesk`, and
`onedesk/locale/ar.po` and `de.po` are kept complete in the repo.

**Complete does not mean every msgstr is filled.** Our POT carries the strings
whose text frappe, erpnext or hrms already say somewhere of their own —
"Salary Slip", "Company", "Status" — because our sidebar and workspace name
those doctypes. Those we leave empty: babel drops an empty entry from the
compiled MO, and `get_translations_from_apps` merges every installed app's
catalogue, so the reader gets hrms's translation rather than a second copy of
it that we then have to keep in step.

What we do translate is our own strings, plus the few upstream leaves blank or
says in the wrong sense — "Leave" translated as the verb where our rail means
the noun. Ours wins there because onedesk is installed last and its MO is
merged last.

`tests/test_translations.py` reads all of that back: nothing in the POT is left
without a translation from somewhere, nothing is translated that the POT no
longer says, and a `{0}` in the English is a `{0}` in both translations.

Which means a wording change is a translation change. Rewrite the English,
regenerate the POT, and fill in the two `msgstr` lines in the same commit.

**`rules.py` is the one exception to `_()`.** It must not import frappe, so its
signal sentences are wrapped in a local `N_` — a no-op marker babel extracts
anyway — and `clock.py` translates them at the point it shows one.
