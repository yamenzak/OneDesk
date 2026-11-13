---
name: wording
description: How One words anything a person reads. Load it before writing or changing any label, field description, Select option, heading, note, button, column, status, empty state, error, toast, confirmation, notification, tour step, Help page or agreement clause — in doctype JSON, Python _(), desk JS __() or a Vue island — and before translating one into Arabic or German.
---

# Wording

**Do not compose. Reuse.** Every situation on a screen has a sentence that
frappe, ERPNext or any SaaS admin already says for it. Find it and change
the noun. When there is none, write the most ordinary version, the one
nobody would notice. The test: would it look out of place two rows above
frappe's `Allow Login using Mobile Number`?

The words are a product reporting a fact, never a person talking. Point 13
of `docs/STANDARD.md` holds them (`python3 scripts/lint.py --point 13`);
`docs/WORDING.md` keeps the reasons.

## The phrasebook

**Label** (field, column, tab, section, tour step). Title Case noun phrase,
five words or fewer, no full stop, no article or pronoun. A Check starts
with the verb: `Allow`, `Enable`, `Send`, `Show`, `Prevent`, `Require`.
Units in brackets. Another doctype by its exact name. ERPNext's own label
stays (`field-keeps-erpnexts`).

    Attachment Limit (MB)      Enable Scheduled Jobs      Default Letter Head

**Field description.** Most fields have none. When there is one: one
sentence, at most 130 characters, saying what the system does
(`descriptions-plain`, `copy-descriptions`). frappe's openers:

    If enabled, …   Leave empty to …   Set to 0 to …   Defaults to …
    Requires …      Example: …         Only …          Number of days after which …

**Heading:** ERPNext's name for what is listed. **Note:** usually none.
**Button:** a verb and a noun, `Send Invite`; the verb follows through to
"Invite sent." **Empty state:** `No invoices yet`.

**Error.** What is wrong, then what to do if not obvious, the value in `{0}`:
`{0} is required.`, `Could not save the template.`, `Your role doesn't allow
changing this.`

**Confirmation.** The question is the title, the effect one line under it,
the button names the act, never Yes or OK.

    Delete Grant Plastics?     Its contacts and addresses stay.     [Delete Customer]

**Activity.** Past tense, the reader as "You": `You changed 5 fields`,
`Huda submitted this`; a field's line is `Field old → new`.

**Tour step:** a noun phrase title; its text says what the thing does.

**Notification.** `about` starts with the moment: "When somebody applies for
leave." The subject says what happened to what, the message what to do
next, the button a verb and a noun. Facts on one line: `Due 20 Oct · Mansour
Villa`. Its slots are named, never numbered (`notify-slots-named`).

**Agreement clause.** The `legal` skill. A version is `changelog`'s, a Help
page `docs`'s.

## Claude's habits, and what to write instead

Each was on a screen in this app.

A line that balances two halves, or sounds like a saying.

    ✗ A live frame from the camera, never a file. Says who, not where.
    ✓ Taken with the camera.

The product as the actor, explaining its own workings.

    ✗ One fetches it a few times a day.       ✓ Updated a few times a day.

A pronoun with nothing before it to point at.

    ✗ Its logo comes from here.   ✗ Its Items
    ✓ Used to find the source's logo.   ✓ View Items

Two thoughts joined by a semicolon, a colon or a dash.

    ✗ Older ones are deleted; 0 keeps them all.   ✓ Set to 0 to keep all items.

The reason instead of the effect.

    ✗ Empty is the kind's usual, such as Dubai.
    ✓ Leave empty to use the default. Example: Dubai

A person's turn of phrase, or a clause where a button should be.

    ✗ This doesn't read as a workbook.   ✓ This file is not a workbook.
    ✗ Where I Am                         ✓ Use Current Location

Telling the reader how to use the screen.

    ✗ Open one to change it.   ✗ Click a day for details.   ✓ (nothing)

Who else is allowed, instead of what is true for the reader.

    ✗ Only a Mail Manager or an administrator can change this.
    ✓ Your role doesn't allow changing this.

The first person, and reassurance.

    ✗ Thank you. We are building your workspace.
    ✓ Payment received. The workspace is being built.

Our own coinages for what frappe names: never "carry", "came with", "take
back", "as it came", "Kind", "Rules". Say In List View, Depends On, Fetched
From, Type, Properties. The banned words are `copy-banned`'s list; simply,
just, please, seamless, "Are you sure", "Something went wrong" are on it.

## Names

A product is one word: OneMail, never "One Mail"; "One" alone is the
product. A name is typed once, in its manifest, and read everywhere else
(`names-are-code`): Python `_("Edit in {0}").format(registry.name("one_doc"))`,
desk JS `__("Edit in {0}", [onedesk.names.of("one_doc")])`, an island the
kit's `name("one_doc")`, Help, a version or a notification `{one_doc}`. A
name alone is not translated. A thing is called what ERPNext calls it, the
name Ctrl+K finds it by (`rail-says-erpnexts`).

## Translation

A wording change is a translation change, in the same commit (`translated`,
`placeholders`). Never translate a bare list of English strings.

1. `bench generate-pot-file --app onedesk`
2. `../../env/bin/python scripts/translate.py todo > /tmp/todo.json`: each
   string with what it is, its files, the strings around it with their
   Arabic, and the glossary's words for its terms.
3. Fill each `ar` and `de`, reading it in that frame. "Open" beside invoice
   statuses is مفتوحة, not فتح; "Bank's No" on a guarantee is its number at
   the bank, not رقم البنك.
4. `../../env/bin/python scripts/translate.py apply /tmp/todo.json`, which
   refuses changed placeholders and a glossary term said another way.
5. `bench compile-po-to-mo --app onedesk`

**The glossary** (`onedesk/locale/glossary.csv`) is one word per term
(`glossary-kept`): اعتماد for Approve, never وافق; مخزون for Stock; مسودة for
Draft. Buttons take the verbal noun, as frappe's do: إضافة, حفظ, never أضف. A
missing term is added there first. Upstream's Arabic is not a source: hrms
says غادر for Leave. `glossary_debt.json` only shrinks (`glossary-debt`).

**German** is gender-neutral for people: Mitarbeitende; rephrase around the
person ("Wer einen Antrag stellt"). Kunde and Lieferant stay.
**Arabic** is Modern Standard, as a Gulf business product writes it.

## Before handing back

Words in a mock pass this skill before they are drawn. Read every new string aloud where it appears, then
`../../env/bin/python scripts/lint.py`. A failure means the string is
wrong: rewrite it from the phrasebook, never just enough to slip past.
