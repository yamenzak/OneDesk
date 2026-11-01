---
name: wording
description: How One words anything a person reads. Load it before writing or changing any label, field description, Select option, heading, note, button, column, status, empty state, error, toast, confirmation, notification, tour step, Help page or agreement clause — in doctype JSON, Python _(), desk JS __() or a Vue island — and before translating one into Arabic or German.
---

# Wording

**Do not compose. Reuse.** Every situation on a screen has a sentence that
frappe, ERPNext or any SaaS admin already says for it. Find that sentence and
change the noun. When there is none, write the most ordinary version you can,
the one nobody would notice.

The test for every string: would it look out of place two rows above
frappe's `Allow Login using Mobile Number`? If it would, rewrite it.

The words are a product reporting a fact, never a person talking.

## The phrasebook

**Label** (field, column, tab, section, dialog, tour step). Title Case noun
phrase, five words or fewer, no full stop, no article or pronoun inside.
A Check starts with the verb: `Allow`, `Enable`, `Send`, `Show`, `Prevent`,
`Require`. Units in brackets. Another doctype by its exact name.

    Attachment Limit (MB)      Enable Scheduled Jobs      Default Letter Head
    Send Welcome Email         Retirement Age (In Years)  Expected End Date

**Field description.** Most fields have none: hrms's HR Settings has forty
fields and four descriptions. When there is one: one sentence, at most 130
characters, saying what the system does. Start with frappe's openers:

    If enabled, …        Leave empty to …     Set to 0 to …
    Defaults to …        Requires …           Example: …
    Only …               Number of days after which …

**Heading.** The plain name of what is listed, in ERPNext's name for it.
`Custom Fields`, `Purchase Receipt`, `Stock Entry`. Never a coined one.

**Note under a heading.** Usually none. When there is one, a fact the screen
cannot show, at most 70 characters: `The currency can't change once there are
transactions.`

**Button.** A verb and a noun, no article: `Add Field`, `Send Invite`,
`Export`, `Reset`. The same verb follows through: `Publish` → "Published."

**Empty state.** `No custom fields`, `No matching forms`, `No invoices yet`.

**Error.** What is wrong, then what to do if that is not obvious. The
thing named, the value in `{0}`.

    File {0} does not exist.
    Expiration date must be in the future.
    Could not save the template.
    {0} is required.
    Your role doesn't allow changing this.

**Toast.** Past tense, the button's verb: `Template saved.`, `Invite sent.`,
`{0} moved to OneCloud.`

**Confirmation.** The question, then the effect. The confirm button repeats
the verb.

    Delete comment?
    Reset Item? This removes all custom fields and changes.

**Notification.** `about` starts with the moment: "When somebody applies for
leave." The subject says what happened to what; the message says what to do
next; the button is a verb and a noun (`Review Request`). Facts on one line:
`Due 20 Oct · Mansour Villa`.

**Agreement clause.** "We" is Four Degree Labs, "you" is the organisation. One
point per sentence, at most 30 words, a number where there is one, no
legalese (shall, herein, hereby, pursuant to, notwithstanding). English only.

## Claude's habits, and what to write instead

These are what make copy read as written by a model. Each was on a screen in
this app.

A line that balances two halves, or sounds like a saying.

    ✗ A live frame from the camera, never a file. Says who, not where.
    ✓ Taken with the camera.

The product as the actor, explaining its own workings.

    ✗ One fetches it a few times a day.
    ✓ Updated a few times a day.

A pronoun with nothing before it to point at.

    ✗ Its logo comes from here.        ✗ Its Items
    ✓ Used to find the source's logo.  ✓ View Items

Two thoughts joined by a semicolon, a colon or a dash.

    ✗ Older ones are deleted; 0 keeps them all.
    ✓ Set to 0 to keep all items.

The reason instead of the effect.

    ✗ Empty is the kind's usual, such as Dubai.
    ✓ Leave empty to use the default. Example: Dubai

A person's turn of phrase.

    ✗ This doesn't read as a workbook.     ✓ This file is not a workbook.
    ✗ The record didn't take this table.   ✓ Could not add the table to {0}.

Telling the reader how to use the screen.

    ✗ Open one to change it.   ✗ Click a day for details.   ✓ (nothing)

Who else is allowed, instead of what is true for the reader.

    ✗ Only a Mail Manager or an administrator can change this.
    ✓ Your role doesn't allow changing this.

The first person, and reassurance.

    ✗ Thank you. We are building your workspace.
    ✓ Payment received. The workspace is being built.

Our own coinages for things frappe already names: never "carry", "came with",
"take back", "as it came", "Kind", "Rules". Say In List View, Depends On,
Fetched From, Type, Properties.

Words never shown: simply, just, easily, please, utilise, leverage, seamless,
powerful, robust, note that, in order to, functionality, "Are you sure",
"Something went wrong", any more, of its own, beside, and the names Frappe,
ERPNext and press.

## Names

A product is one word: OneMail, OneHR, OneCloud, never "One Mail". Read the
name from `MARKS[id].name` rather than typing it. "One" alone is the product.
A thing is called what ERPNext calls it, the name Ctrl+K finds it by.

## Translation

A wording change is a translation change, in the same commit.

1. `bench generate-pot-file --app onedesk`
2. Fill the new `msgstr` in `onedesk/locale/ar.po` and `de.po`. Keep every
   `{0}`. Before choosing a word, grep both files for how it is already
   translated and use that. Leave empty a string frappe, erpnext or hrms
   already translate ("Salary Slip", "Status").
3. German is gender-neutral: rephrase around the person ("Wer einen Antrag
   stellt", "Beschäftigte", "Personen") rather than "Mitarbeiter".
4. `bench compile-po-to-mo --app onedesk`

## Before handing back

Read every new string aloud, in the place it appears. Then run the wording
guards, which take seconds, instead of the whole suite:

    python3 -m pytest -q tests/guards/test_wording.py tests/guards/test_copy.py \
      tests/test_names.py tests/guards/test_translations.py \
      tests/guards/test_legal.py tests/guards/test_erpnext_names.py

A guard failure means the string is wrong, not the guard. Rewrite the string
using the phrasebook above; do not reword just enough to slip past the regex.

`docs/WORDING.md` is where the reasons live.
