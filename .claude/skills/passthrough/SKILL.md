---
name: passthrough
description: How to do a passthrough — one careful pass over a stated scope (a screen, a module, a flow, a set of files, the whole app) against named standards, ending with every finding fixed or written down and the scope marked passed. Load it before any review, walk, audit, sweep, cleanup or "go through X" request, whatever the code and whatever its focus (UI, words, docs, legal, performance, security, tests), and before calling one finished.
---

# Passthrough

A passthrough is one pass, not a tour. It has a scope you can list, a
standard you can name, and an end you can prove: every finding fixed or
written down, the gates green, the scope marked. Many passes have been done
here, each with its own focus; what keeps the next one from repeating them
is that this one says exactly what it covered and leaves a mark.

## Before starting: write the three lines

In the conversation, before touching anything:

- **Scope.** The list, item by item: the screens (as the stamp names them,
  `Form/Sales Invoice`, `List/Customer`, `onemail`), the files, or the flows
  ("pay a supplier invoice"). If it can't be listed it is too big; split it.
- **Standard.** The skills and documents this pass checks against: `ui`,
  `ux`, `wording`, `docs`, `changelog`, `legal`, a module's AGENTS.md, a
  READY point, a guard. A pass with no named standard turns into taste.
- **Done.** What has to be true at the end of each item, usually: looked
  at, fixed, gates green, docs and version updated, stamped, committed.

Then check what earlier passes already did: `docs/PASSOVER-LOG.md` (where
every area stands, and when it was last passed), `git log --grep` the
scope, the module's SCRATCHPAD, and `one_interface/stamps.py` `PASSED`. A
screen stamped Passed is not passed again unless it changed since its day.

A screen's pass holds it to `docs/PASSOVER.md`'s seventeen points. A
module's pass holds it to `docs/READY.md`'s fourteen points, through its
mechanisms (1 to 19), and to the lessons at the end of READY.md.

## What every pass looks at

Whatever the focus, these are on the list unless the three lines say why
not. Each was missed once by a pass that thought it was done.

- **Sizes.** 1440, a tablet (820), a phone (390), and a pane beside the
  screen. The tablet finds what neither end does.
- **Looks.** Light and dark, the default palette and one other, Arabic
  (right to left) and German (the longest words).
- **People.** Each role whose work it is, and one who may not: what they
  can't do is hidden or refused, never an error.
- **States.** Empty, one row, many, loading, an error on purpose, a draft,
  a cancelled record, a record in another currency.
- **Live.** It changes when the record changes elsewhere
  (`frappe.realtime`); dates, numbers, money and time zone are the reader's.
- **Keys.** Its shortcuts are declared in the module's `shortcuts.py` and
  work in that view and no other; nothing clashes in ShortcutCenter;
  Escape closes, Tab reaches every control, focus is visible.
- **The frame.** On OneInterface through its adapter or island kit, tokens
  only, frappe's own parts placed and not redrawn.
- **Its part of every centre.** Settings (ControlCenter), `abilities.py`
  (AccessCenter), `notifications.py`, `legal.py` (TrustCenter), `ai.py`
  (AICenter), `shortcuts.py` (ShortcutCenter), `docs/` (HelpCenter),
  `docs/changelog/` (UpdateCenter), and the foot that opens them.
- **OneAI.** Everything a person does here is a card, or is in `NOT_FOR_AI`
  with the reason.
- **Notifications.** What each of its events sends, to whom, on which
  channels, in plain words, and that NotificationCenter lists each type
  (`notifications.py`, the `ui` skill's mails).
- **Docs.** Its AGENTS.md says how it works now, its Help page says what a
  person does now with pictures of the screen as it is, and What's New
  says what changed (`docs` and `changelog` skills).
- **Legal.** What it does with data is in its `legal.py`; a new service,
  company or kind of data moves the agreements with a version (`legal`
  skill).
- **Demo.** The demo company has it, and a check in the module's
  `checks.py` reaches every whitelisted method (`test_coverage.py`).
- **First visit.** Its tour and its setup steps still match the screen.
- **What ERPNext already does.** Its statuses, its checks on save, its
  mappers, precision and units, and `base_` amounts in figures.
- **Several companies.** It works for a workspace with more than one
  company, and looks unchanged with one. Where the company decides
  something it is shown and defaulted (the reader's default, the
  employee's, the party's); lists offer it as a column and a filter; Homes
  and figures are one company's at a time, in its currency, never added
  across; pickers offer only that company's accounts, warehouses, cost
  centres, tax templates and series; prints carry that company's letter
  head; a person limited to a company by a User Permission sees only its
  records; the demo has a second company with records, and a check. Each
  module's pass does this for its own screens (CLAUDE.md, Several companies).
- **Printing.** A record that leaves the company prints from our own
  format, in Arabic too, under the letter head.
- **Portal.** What it shows customers and suppliers (`portal.py`), and a
  signed link opens that record and no other.
- **Search and reach.** Its records are found in Ctrl+K and in pickers, and
  nothing the reader can't open is on a rail, in search or in a picker.
- **Security.** Every whitelisted method checks permission, a write is
  POST only, and a guest page gives away nothing it shouldn't.
- **Speed.** Requests, size and time to a usable screen, measured before
  and after: requests, KB and time to a usable list, form, home and centre.
- **A fresh site.** It works on a new workspace straight after the setup
  wizard, not only on the demo.
- **Intake.** Which mails and files should make or change its records, and
  whether OneAI's reading does.
- **Deleting.** What deleting it does: the Recycle Bin brings it back,
  links are swept, the audit log has it.
- **Upstream.** What we override of frappe's, ERPNext's or HRMS's is read
  again against their newest code (`scripts/overrides.py`).

## Each item, in this order

1. **Make it real.** Seed demo data if the item is empty; sign in as the
   person whose work it is (the `ui` skill's list of demo users). Read the
   code behind it before judging what it does.
2. **Look.** The screen at 1440 and at 390, in Arabic and in the dark
   theme, at 2x cropped to each part; the empty state and one error on
   purpose. For code: run it, read its tests, read what calls it.
3. **Hold it to each standard**, one at a time, writing the findings as a
   list. A finding names the place and the rule it breaks.
4. **Fix all of it**, where it is made (the renderer, the registry, the
   shared helper), never by patching this one item. A fix that only the
   user can decide is a question, asked once, with a recommendation; the
   rest of the item carries on.
5. **Look again** at what changed, the same way as step 2.
6. **Close it**: the gates (below), translations for every new string
   (`bench generate-pot-file`, `scripts/translate.py todo` and `apply`,
   then `bench compile-po-to-mo`; the glossary wins, so reword the English
   rather than fight it), the module's Help page and its pictures if what
   people see changed (`docs` skill), a version (`changelog` skill), the
   overrides ledger if a frappe method is wrapped (`scripts/overrides.py`),
   and for a screen its entry in `stamps.py` `PASSED` with today's day and
   this pass's name.
7. **Look again on the record.** A minor or major version makes a ready
   module's hand looks stale (`ready.MODULES[...]["checked"]`). Commit the
   work, then re-date each look you actually took to that commit, in a
   second commit.
8. **Commit** the item, or a few small ones, with the findings and what was
   done in the message.

## Rules that keep a pass honest

- **The scope is the scope.** Something wrong outside it goes in that
  module's SCRATCHPAD, one line, not into this commit.
- **Fix, don't note,** inside the scope. A list of findings handed back
  with nothing fixed is a report, not a pass.
- **Measure what can be measured** before and after: counts of strings,
  guards, untranslated entries, warnings, files.
- **Never call an item passed from the code alone,** or from a screenshot
  of a record that already existed. Make one.
- **A guard that fails is the item failing,** not the guard. Rewriting a
  guard to pass is a decision for the user.
- **The browser suite is not a gate.** Run one spec by name only when
  asked.
- **Stop at the end of the list.** A pass that keeps finding new scope is
  two passes; finish this one and say what the next would be.

## Claude's passthrough habits, and what to do instead

- **Calling it done after looking at the desktop in English.** Phone,
  Arabic and dark find a third of the problems.
- **Fixing the symptom on one screen.** The next screen has it too; fix
  the part that draws it.
- **Forgetting the paperwork.** A changed screen with an old Help picture,
  no version and no translation is not passed.
- **Forgetting the log.** A pass that leaves `PASSOVER-LOG.md` and the
  stamps as they were is redone by the next one.
- **Adding a mechanism and not a line here.** A new centre, registry or
  guard that every module must answer goes into **What every pass looks
  at** in the same commit.
- **Re-doing a pass that was already done** because nothing said it was.
  Read the log and the stamps first, and leave both behind.
- **Turning one pass into a redesign.** Changes the user did not ask for
  go to them as a question.

## Finishing

Every item is stamped or listed as not passed with the reason, and the
area's row in `docs/PASSOVER-LOG.md` says what this pass did and its day
(the log is kept short: a row per area, not a row per pass). Run the
gates, which take minutes between them:

    python3 -m pytest -q
    bench --site onedesk.localhost execute onedesk.one_demo.check.run
    python3 scripts/overrides.py --check && python3 scripts/docs.py --check
    cd frontend && npx vitest run && npx eslint src && npx vite build   # when frontend source changed

READY.md's **The gates** is the full list. A test that failed before this
pass is named in the report, not hidden and not fixed in this commit.

Report in one or two sentences: the scope, how many items passed, the one
thing left open. The commit messages carry the detail.
