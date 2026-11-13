# How a field is worded

The rules as they are applied are `.claude/skills/wording/SKILL.md`, which
Claude Code loads before writing anything a person reads. This page is the
reasoning behind them and what each guard checks.

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

## A notification's sentence

Every kind of notification says **when** it is sent, in one sentence that
starts with the moment: "When somebody applies for leave.", "Every morning,
…", "The day before your exit interview." Said from the reader's side where
the reader is who gets it ("When your leave application is approved…").
Never "the same" as another kind: a kind that is the same event said another
way `follows` it and is not listed on its own.

**Who** it goes to is `to`, apart, because a person's own page never needs it
(it is them) and the workspace's page always does: "Their leave approver".
`tests/test_notify.py` holds both.

**The subject says what happened and to what; the message says what to do
next.** The button is the mail's only link, never an anchor in the message.
Where "Open" and the record's kind would be wrong, the type's `button` says
it, a verb and a noun: `Review It`, `Confirm Request`. A task's or project's
facts go on one line, `Due 20 Oct · Mansour Villa`, not a sentence each.
Every default is read in its frame, in English and in Arabic.

## What is out

No metaphor, no anecdote, no rhetorical contrast. All three of these were in
this app and are gone:

    A router reboot stops locking everybody out on a Monday.
    A system that locks a plumber out at a customer's door is a system they stop using.
    A live frame from the camera, never a file. Says who, not where.

No clipped, telegraphic register either: a pronoun with nothing before it to
point at ("Its logo comes from here", a button called `Its Items`), two
thoughts glued with a semicolon ("…as new ones arrive; 0 keeps them all"),
and the product explaining its own workings ("One fetches it a few times a
day"). Name the thing, and use frappe's openers: `View Items`, "Set to 0 to
keep all items.", "Used to find the source's logo." `test_wording.py` holds
every module's field help and every desk and doctype script to it.

No second person plural about the workforce ("Employees may clock themselves
in"), no wink at the reader, no sentence that is there because it reads well.
The test is whether the line would look out of place two rows above
`Allow Login using Mobile Number`.

## A product's name

A product is written as one word: **OneMail**, **OneHR**, **OneAdmin**, never
"One Mail". "One" on its own is the product itself. On screen the "One" is at
a light weight and the rest at the weight around it, as the marks letter it,
and in a sentence the product's mark goes before its name ("Choose from
OneCloud"); a label that is only the name ("OneCloud" under its own icon)
draws no second one. `public/js/brand.js` does that to every name the desk
draws and `kit/Branded.vue` in the islands, so nothing is written with a span
by hand.

A Frappe module or doctype named before this rule keeps its id ("One HR",
"One Admin Settings"), because an id is never renamed. Where the desk shows
one, `locale/en.po` gives it the product's name, as ar.po and de.po do in
theirs. `tests/test_names.py` refuses a string on screen with the name
spaced, and an id the English catalogue does not name.

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

## On a Screen

Headings, notes under a heading, buttons, column names, badges, empty states
and confirmations read like any good SaaS product. Plain words a person
already knows, and nothing clever.

**A thing is called what ERPNext and frappe call it.** A rail row, a list's,
report's or page's heading, a crumb, a field's label, a column and a status
say the name ERPNext gives the doctype, report, field or status — the name
Ctrl+K finds it by, and the name its own form, its messages and the
reader's training use. `Purchase Receipt`, not `Receipts`; `Stock Entry`,
not `Stock Movements`; `Expected End Date`, not `Due`; `Partially
Depreciated`, not `In Use`. A page of ours that gathers several kinds is
named in ERPNext's words for what it does (`Reorder`, `Asset Maintenance`,
`Batch and Serial No`), or for the ERPNext page it replaces (`Stock
Summary`). A filtered list is called what ERPNext's own sidebar calls it
(`Credit Note`, `Debit Note`, `Profit and Loss`). A capital fixed or a
section heading left blank is not a rename. OneInventory, OneProject, OneTask,
OneBook and OneCRM are held to it by `tests/guards/test_erpnext_names.py`.

**A heading is the plain name of what is listed.** `Custom Fields`, not
`Fields Added Here`. `Changed Fields`, not `Fields Changed Here`.

**Most sections have no note.** The heading and the table say enough. A note
is there only for a fact the screen can't show, in a few words:
`Custom levels sit between User and Manager.`,
`The currency can't change once there are transactions.` It never tells
people how to use the screen ("Open one to change it", "Click a day for
details"), never explains how the machinery works, never runs two clauses
together, and never narrates OneAI. At most 70 characters.

**Use frappe's words.** In List View, Depends On, Fetched From, Non Negative,
Length, Type, Properties, Standard Field. Not our own coinages: never
"carry", "came with", "take back", "as it came", "Rules", "Kind".

**A button is a verb and a noun.** `Add Field`, `Reset`, `Export`. No article.

**An empty state is short.** `No custom fields`, `No extensions`,
`No matching forms`. Not "Nothing added to Item yet." or "Nothing runs on
Item".

**A confirmation asks the question and states the effect.**
`Reset Item? This removes all custom fields and changes.`

Before and after, from the Customize page:

    Fields Added Here
    Ask OneAI to add one: it asks what the field is for, suggests how it is
    checked and shown, and which other forms should carry it.

    Custom Fields
    Ask OneAI to add or change a field.

The guard below checks the part a machine can see: no colon or semicolon
joining two clauses, no em dash, nothing over 140 characters, no "Open one
to…" or "Click a…", and no note over 70 characters. The rest is
checked on every screen of the passover.

## OneInterface's limits

A module on its way to ready (`onedesk/one/ready.py`, `docs/READY.md`) is
held to hard limits on top of everything above, by `tests/guards/test_copy.py`:

- **A heading is five words or fewer.** A tab, a panel, a dialog, a section,
  a group, a field's label, a tour step's heading.
- **A description is one sentence.** So is a hint, the text a search box or
  an icon shows on hover. It says what the thing is or does, never how to use
  the screen.
- **Words we never show:** simply, just, easily, please, utilise, leverage,
  seamless, powerful, robust, note that, in order to, functionality, "Are you
  sure", "Something went wrong", and the names of the software One is built
  on.

Three before and after pairs, from OneMail's settings:

    Only a Mail Manager or an administrator can change this.
    Your role doesn't allow changing this.

    The name shown with the address on every email sent from this mailbox. Leave empty to use the default.
    Shown with the address on every email sent from this mailbox, or the default name if empty.

    For anything urgent, please write to Samir at samir@one.test.
    For anything urgent, write to Samir at samir@one.test.

The first says what is true for the reader, not who else is allowed. The
second is one sentence. The third drops a word that only softens.

## A message

An error, a confirmation, a toast and the line under a dialog say what
happened or what to do, in the words any SaaS product uses.

    Letter head {0} does not exist.
    Could not save the template.
    {0} saved to OneCloud, in the same folder as this workbook.
    Column {0} was removed from the sheet. Undo the change, or reopen the workbook from the record.

Not a person's turn of phrase. These were all on a screen:

    This doesn't read as a workbook.
    The record didn't take this table.
    It goes in OneCloud › Workbook Templates, where everyone in the company can start from it.
    This formula reads itself, through the cells it reads.

`test_a_message_says_what_happened` reads every `_()` and `__()` in the app,
the desk's scripts and the islands for the phrasings that keep coming back:
"any more", "of its own", "doesn't read", "works out to", "didn't take",
"beside", "couldn't be made", "wasn't kept", "where everyone", "isn't there",
"No {0} called". It cannot judge the rest, so a person still reads every
message on the screen it appears on.

## The agreements

What One promises is written precise and plain, which is what the GDPR asks
of it (Art. 12), and never in legalese.

- **We** is Four Degree Labs and **you** is the organisation, or the person
  where a policy is theirs. Never "the Company", "the Customer" or "the
  Provider".
- **One point to a sentence**, and no sentence over 30 words. A list of
  what is sent is one point.
- **A number where there is one**: 72 hours, 30 days, two months.
- **No legalese**: not shall, herein, hereby, thereof, whereas, pursuant to,
  notwithstanding, aforementioned, forthwith or in no event.
- **Nothing promised that isn't built.**
- **In English only**, like Help: what is agreed to is the words, and a
  translation would be a second text. What surrounds them in TrustCenter is
  translated.

`tests/guards/test_legal.py` holds every clause to the legalese rule, and
the clauses of a module going through docs/READY.md to the sentence rule too.
Every other module's are rewritten to it as it goes through.

## The guard

`tests/guards/test_wording.py` holds every doctype and every custom field in the app
to what can be checked by machine: a description of at most 130 characters and
two sentences, with no first person, no em dash and no colon except after
`Example`; a label in Title Case with no full stop, at most 60 characters, that
is a name rather than a sentence: no article, pronoun or verb inside it, "Is"
and "Has" only to start a checkbox, and "I …" only for a consent checkbox
("The Old App Has" was a label here). A Select's options, a dialog's fields and
a report's columns, in Python and in `public/js`, are held to the same. The rest of
this page — no reasoning, frappe's openers, most fields with no description at
all — is still read by a person.

`test_what_a_screen_says_is_plain` reads every `__("…")` in `public/js` for the
On a Screen rules, with no exceptions. A label and its value
(`Default: {0}`) is not a joined clause and is allowed.

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

`tests/guards/test_translations.py` reads all of that back: nothing in the POT is left
without a translation from somewhere, nothing is translated that the POT no
longer says, and a `{0}` in the English is a `{0}` in both translations.

Which means a wording change is a translation change. Rewrite the English,
regenerate the POT, and fill in the two `msgstr` lines in the same commit.

**One word for one thing.** A translation was written from a bare list of
English strings, so "Approve" came out four ways across the screens and
buttons took two grammatical forms. `onedesk/locale/glossary.csv` now holds
one Arabic and one German word per term, `scripts/translate.py` hands each
new string over with its kind, its place and its neighbours, and
`tests/guards/test_glossary.py` refuses a new translation that says a term
another way. What was already wrong is listed in
`onedesk/locale/glossary_debt.json`, which only shrinks: point 13 of
`docs/STANDARD.md` clears it screen by screen.

**`rules.py` is the one exception to `_()`.** It must not import frappe, so its
signal sentences are wrapped in a local `N_` — a no-op marker babel extracts
anyway — and `clock.py` translates them at the point it shows one.
