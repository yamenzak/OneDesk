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

**Confirmation.** The question is the dialog's title; the effect is one
line under it; the button names the act, never Yes or OK.

    Delete Grant Plastics?         Its contacts and addresses stay.      [Delete Customer]
    Cancel this invoice?           It stays in the books as cancelled.   [Cancel Invoice]

**Card on a record's head.** What the figure is and over what span; the
value is only the number. `Billed in 12 months`, `Overdue`, `Open Orders`.

**Activity.** One line per person per sitting, in the past tense with the
reader as "You": `You changed 5 fields`, `Huda submitted this`, `1 row
added, 1 row removed`. A field's line is `Field old → new`; long text says
`edited`.

**Window controls.** `Enlarge`, `Make Smaller`, `Close`, `Back`. A tour
step's title is a short noun phrase (`Find What You Need`) and its text
says what the marked thing does, never where it is.

**Notification.** `about` starts with the moment: "When somebody applies for
leave." The subject says what happened to what; the message says what to do
next; the button is a verb and a noun (`Review Request`). Facts on one line:
`Due 20 Oct · Mansour Villa`.

**Agreement clause.** "We" is Four Degree Labs, "you" is the organisation. One
point per sentence, at most 30 words, a number where there is one, no
legalese (shall, herein, hereby, pursuant to, notwithstanding). English only.
The `legal` skill has the rest. A version's words are the `changelog`
skill's, a Help page's the `docs` skill's.

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

A clause where a button should be: a pronoun, a place, no verb.

    ✗ Where I Am                  ✓ Use Current Location

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

A product is one word: OneMail, OneHR, OneCloud, never "One Mail". "One"
alone is the product. A name is typed once, in its manifest, and read
everywhere else (tests/guards/test_names.py): Python
`_("Edit in {0}").format(registry.name("one_doc"))`, desk JS
`__("Edit in {0}", [onedesk.names.of("one_doc")])`, an island the kit's
`name("one_doc")`, and Help, a version or a notification's words
`{one_doc}`, filled in when it is shown. A name alone is not translated:
`registry.name("one_ai")`, not `_("OneAI")`.
A thing is called what ERPNext calls it, the name Ctrl+K finds it by.

## Translation

A wording change is a translation change, in the same commit. Never
translate a bare list of English strings: each one is translated where it
is shown.

1. `bench generate-pot-file --app onedesk`
2. `../../env/bin/python scripts/translate.py todo > /tmp/todo.json` lists
   every string nobody translates yet, with what it is (a field label, a
   notification subject, a print format label), the files it is in, the
   strings around it with their Arabic, and the glossary's words for the
   terms it uses. A string frappe, erpnext or hrms already translate is left
   to theirs and is not listed.
3. Fill each entry's `ar` and `de`, reading it in that frame. "Open" next
   to invoice statuses is مفتوحة, not فتح. "Bank's No" on a bank guarantee
   is the guarantee's number at the bank, not رقم البنك.
4. `../../env/bin/python scripts/translate.py apply /tmp/todo.json` writes
   them, and refuses one whose placeholders differ from the English or that
   says a glossary term another way.
5. `bench compile-po-to-mo --app onedesk`

**The glossary** (`onedesk/locale/glossary.csv`) is one word per term: اعتماد
for Approve, never وافق or موافقة; مخزون for Stock; مسودة for Draft. Buttons
take the verbal noun, as frappe's do: إضافة, حفظ, إرسال, never أضف. A term
missing from it is added there, with its Arabic and German, before it is
used. Upstream's own Arabic is not a source: hrms says غادر for Leave.

**German** is gender-neutral for people: Mitarbeitende, not Mitarbeiter;
rephrase around the person ("Wer einen Antrag stellt"). A customer or
supplier is an organisation, so Kunde and Lieferant stay.

**Arabic** is Modern Standard, as a Gulf business product writes it.
Placeholders stay as they are.

`onedesk/locale/glossary_debt.json` lists what was already wrong when the
glossary came in. It is cleared screen by screen in the final checks, and
a string fixed is taken out of it in the same commit.

## Before handing back

Words in a mock are product words: they pass this skill before they are
drawn, not after. Read every new string aloud, in the place it appears. Then run the wording
guards, which take seconds, instead of the whole suite:

    python3 -m pytest -q tests/guards/test_wording.py tests/guards/test_copy.py \
      tests/test_names.py tests/guards/test_translations.py tests/guards/test_glossary.py \
      tests/guards/test_legal.py tests/guards/test_erpnext_names.py

A guard failure means the string is wrong, not the guard. Rewrite the string
using the phrasebook above; do not reword just enough to slip past the regex.

`docs/WORDING.md` is where the reasons live.
