---
name: passthrough
description: How to do a passthrough — one careful pass over a stated scope (an app, a screen, a flow, a feature just built, a set of files, the whole app) against named standards, ending with every finding fixed or written down and the scope stamped. It is also the definition of done for a new app or feature. Load it before any review, walk, audit, sweep, cleanup or "go through X" request, before calling an app or a feature finished, whatever its focus (UI, words, docs, legal, permissions, OneAI, notifications, performance, security, tests).
---

# Passthrough

A passthrough is one pass, not a tour. It has a scope you can list, a
standard you can name, and an end you can prove: every finding fixed or
written down, the gates green, the scope stamped. The same list is what
"done" means when an app or a feature is built: a feature answers the
items it touches, a new app answers all of them.

## Two kinds of app

Every app in One is one of two kinds, and the kind decides how its screens
are made. An app's kind is how it is built, not what it is about.

**On ERPNext and HR.** Its records are ERPNext's or HRMS's (or frappe's
own): OneBook, OneInventory, OneCRM, OneHR, OneProject, OneTask.

- **Native as far as it goes.** frappe's own list, form, report and tree,
  dressed by OneInterface (the renderer, which already covers desktop,
  phone, both themes and every language) and by the registry. That keeps
  ERPNext's business logic, its statuses and checks, and every upstream
  update working without a port.
- **The exceptions are named.** A cornerstone record people live in may
  have a page of its own: `tiers.PAGES` (Project, Project Template, Item)
  and, next, `tiers.NEXT_PAGES` (Opportunity, Lead, Employee, Job
  Applicant; Customer belongs with them). An exception gives its reason
  there. Everything else that is an island today (`tiers.SCREENS`) becomes
  frappe's own screen in its app's pass, first, before anything is walked.
- **Never a second copy of ERPNext's logic.** A status, a total, a check on
  save, a mapper, precision, units and `base_` amounts are ERPNext's.

**Custom.** Its records are ours and its screens are a product of their
own, like a standalone SaaS app: OneMail, OneCloud, OneCalendar,
OneDisplay, OneSlide, OneWriter, OneWorkbook, OneStudio, OneAI, OnePortal,
and One's Home and centres.

- **Its own UI, drawn the way the best app for the job does** (Gmail,
  Drive, Google Calendar, Keynote, Linear), with frappe-ui's parts and the
  island kit, on OneInterface's frame. Its row in `docs/ISLANDS.md`, What
  each screen follows, names the app.
- **Live.** It hears change through `frappe.realtime` and redraws, without
  a refresh, wherever two people could look at the same thing.
- **Frappe's formats.** Money, numbers, dates, times, durations and
  quantities print through the kit (`money`, `count`, `hours`, `quantity`,
  `weekdays`) and `frappe.format`, the way the workspace and the reader set
  them, never the browser's own.

A new app says which kind it is in its AGENTS.md first line, and this list
moves with it.

## Before starting: write the three lines

In the conversation, before touching anything:

- **Scope.** The list, item by item: the app, its screens (as the stamp
  names them: `Form/Sales Invoice`, `List/Customer`, `onemail`), a flow
  ("pay a supplier invoice"), or the feature. If it can't be listed it is
  too big; split it.
- **Standard.** This skill's lists, and the others it names: `ui`, `ux`,
  `wording`, `docs`, `changelog`, `legal`, the app's AGENTS.md,
  `docs/PASSOVER.md`'s seventeen points, `docs/READY.md`.
- **Done.** Usually: looked at, fixed, gates green, docs, version and
  translations written, stamped, committed.

Then read what earlier passes did: `docs/PASSOVER-LOG.md` (each area's last
pass), `git log --grep` the scope, the app's SCRATCHPAD, `stamps.PASSED`
and the app's `checked` looks in `ready.MODULES`. Something stamped is not
passed again unless it changed since its day.

## What a pass looks at

Four lists. Each item was once missed by a pass that thought it was done;
leave one out only when the three lines say why. Where a guard holds an
item, run it: a guard holds what is declared to be right, so the hand
checks are what is missing.

### 1. The registry, for every app

What an app declares about itself, in its own folder and in
`ready.MODULES`, so One can show it, guard it, explain it and reach it.

- **Several companies.** It works for a workspace with more than one
  company and looks unchanged with one. Where the company decides
  something it is shown and defaulted (the reader's default, the
  employee's, the party's); lists offer it as a column and a filter; Homes
  and figures are one company's at a time, in its currency, never added
  across; pickers offer only that company's accounts, warehouses, cost
  centres, tax templates and series; prints carry that company's letter
  head; a person limited to a company by a User Permission sees only its
  records; the demo has a second company with records, and a check
  (CLAUDE.md, Several companies).
- **Permissions.** Each thing the app lets a person do fits a role or is an
  ability in its `abilities.py`, shown in AccessCenter; a person given more
  on one record gets it through `rights.grant`; every method our screens
  call on the server checks it, beyond what frappe checks, and a write is
  POST only. *Guards: test_ready, test_roles.*
- **Sharing.** What a person may share of it (a record, a file, a
  workbook) and at which levels, with people here, a customer's or
  supplier's contact, or anyone with a link. Until OneAccess's one Share
  is built (`docs/BACKLOG.md`), note where the app shares its own way.
- **OneAI.** Every action that changes something is a card in its `ai.py`
  `REACH`, or in `NOT_FOR_AI` with the reason; AICenter shows its part; on
  each screen the panel knows where it is and offers the cards that fit,
  and the page context moves with the screen when an island becomes
  frappe's (it was keyed to island names: `item-view`, `stock-on-hand`).
  *Guard: test_ready, for the declaration only.*
- **Notifications.** List the app's events and who waits on each (an
  approver, the person asked, the owner): every one is a type in its
  `notifications.py`, worded by the `wording` skill and listed in
  NotificationCenter, or a line saying why not; its button opens the
  record where the person acts on it. A job that tells keeps who was told
  on the record, never only in the cache, which every deploy clears.
  *Guards: test_notifications, test_ready.*
- **Icons and the record's dressing.** Every record type a person reaches
  has its entry in `ready.MODULES[app]["interface"]`: an icon for each tab
  and field, up to four head cards, its track, its list's states and its
  shortcuts. The guards hold an entry right, not there. *Guard: test_interface.*
- **Legal.** What it does with data is in its `legal.py`: a clause for each
  promise, a subprocessor or service for each company and host it sends
  to; a change moves the agreements with a version (`legal` skill).
  *Guard: test_legal.*
- **HelpCenter and What's New.** Its AGENTS.md says how it works now; its
  `docs/` pages say what a person does, with pictures of the screen as it
  is (`docs` skill); each change is a version in `docs/changelog/`
  (`changelog` skill). *Guards: test_ready, test_docs_media.*
- **Printing.** Every record that leaves the company (to a customer, a
  supplier, an employee, an authority) prints from a format of ours, in
  Arabic too, under the letter head, or is in `NOT_SENT`. *Guard: test_print.*
- **The rest of the centres.** Its settings in ControlCenter, its keys in
  `shortcuts.py` (ShortcutCenter, nothing clashing), its tour and its
  setup wizard slide, and the foot that opens them. *Guard: test_ready.*
- **Demo and checks.** The demo company has its records, made by the
  user whose work it is, and its `checks.py` reaches every whitelisted
  method. *Guards: test_coverage, test_demo.*
- **The atlas.** Every record type, report and page it brings has a way in
  or an answer in `atlas.py`, and nothing a person reaches is open to
  nobody. *Guard: test_atlas.*

### 2. For an app on ERPNext and HR

- **Islands become frappe's**, first: each `tiers.SCREENS` entry of the app
  that is not in `tiers.PAGES` becomes frappe's own list, form or report
  with the registry's dressing, carrying its OneAI context and every link
  to it across. Nothing is stamped that is about to be replaced.
- **A page of its own**, where `tiers.PAGES` names one: it is reached from
  the record, reads like a form, and offers everything the form did.
- **What ERPNext already does**: its statuses, checks on save, mappers,
  precision, units and `base_` amounts, shown, never redone.
- **Upstream.** What we lean on of ERPNext's, HRMS's and frappe's is
  ledgered (`scripts/overrides.py`) and read against their newest code.
  *Guards: test_generated, test_override_signatures.*

### 3. For a custom app

- **A product of its own**, drawn after the app named in ISLANDS.md, on the
  frame and the island kit, tokens only. *Guard: test_islands.*
- **Live**: two people on the same thing see each other's change without a
  refresh (`frappe.realtime`, a room per record or mailbox, nothing sent to
  someone who may not read it).
- **Formatted by frappe**: every figure, date and time through the kit or
  `frappe.format`, in the reader's language, currency and time zone.
  *Guard: test_formats.*
- **Its own checks on the server**: an island's methods are whitelisted by
  us, so each one checks the reader's right itself.

### 4. On every screen, by eye

Each screen in scope gets these, whichever kind its app is.

- **Sizes.** 1440, a tablet (820), a phone (390), and a pane beside it.
- **Looks.** Light and dark, the default palette and one other, Arabic
  (right to left) and German (the longest words).
- **People.** Each role whose work it is, and one who may not: what they
  can't do is hidden or refused, never an error.
- **States.** Empty, one row, many, loading, an error on purpose, a draft,
  a cancelled record, a record in another currency.
- **Keys.** Escape closes, Tab reaches every control, focus is visible, and
  its shortcuts work here and nowhere else.
- **Search and reach.** Its records are found in Ctrl+K and in pickers, and
  nothing the reader can't open is on a rail, in search or in a picker.

### Together

- **It works with the rest of One** where its job needs it: mail about its
  records lands on them (OneMail), their files are in OneCloud, their
  dates in OneCalendar, OneIntake makes or changes them from what arrives,
  OneAI reads and acts on them, the portal shows customers and suppliers
  their part, and a hand-off reaches the next person with the record and
  the one action.
- **Speed**: requests, size and time to a usable list, form, home and
  centre, measured before and after. A `:has()` that restyles the page is
  refused by `test_selectors`.
- **A fresh site**: it works straight after the setup wizard, not only on
  the demo.
- **Deleting**: the Recycle Bin brings it back, links are swept, the audit
  log has it.
- **Empty dates.** frappe reads an empty date as the earliest day, so a
  `<` filter on a date that may be empty matches it; ask `is set` first.
  Three jobs did harm this way in one week.

## Each item, in this order

1. **Make it real.** Seed demo data if it is empty; sign in as the person
   whose work it is (the `ui` skill's demo users). Read the code before
   judging what it does.
2. **Look.** 1440 and 390, Arabic and dark, at 2x cropped to each part; the
   empty state and one error on purpose. For code: run it, read its tests
   and what calls it.
3. **Hold it to each list**, one item at a time, writing findings as a
   list. A finding names the place and the rule it breaks.
4. **Fix all of it where it is made** (the renderer, the registry, the
   shared helper), never by patching this one screen. A fix only the user
   can decide is a question, asked once with a recommendation; the rest
   carries on. While fixing, `python3 scripts/quick.py`; keep
   `node build-islands.mjs --watch` running in `frontend/` while island
   code changes.
5. **Look again** at what changed, the same way as step 2.
6. **Close it.** `python3 scripts/close.py` regenerates docs and the
   overrides ledger, fingerprints a version not yet committed, names an
   app that needs `scripts/version.py`, and counts strings to translate.
   Then write what only a person can: the version's words, the Help page
   and its pictures if what people see changed, and the ar/de strings
   (`scripts/translate.py apply`, then `bench compile-po-to-mo`).
7. **Stamp it** (below), and commit with the findings and what was done in
   the message. Commit only when `quick.py --all` itself reports no
   failure, not when a pipe after it does.

## Stamping

What a pass leaves behind, so the next one starts where it ended:

- **A screen**: its entry in `one_interface/stamps.py` `PASSED`, named as
  frappe routes to it, with the day and the pass's name. On a dev site the
  bottom bar shows it Passed; an island shows its amber stamp until it is
  passed or replaced.
- **An app**: its hand looks in `ready.MODULES[app]["checked"]`, recorded
  after the commit with `python3 scripts/close.py --looked
  one_mail:copy,interface,…`, only for what was looked at; a minor or major
  version makes them stale.
- **The area**: its row in `docs/PASSOVER-LOG.md`, one row per area, saying
  what this pass did and its day.
- **What waits**: anything found outside the scope goes in that app's
  SCRATCHPAD or `docs/BACKLOG.md`, one line.

## Rules that keep a pass honest

- **The scope is the scope.** Something wrong outside it is a line in a
  SCRATCHPAD, not part of this commit.
- **Fix, don't note,** inside the scope. Findings handed back with nothing
  fixed are a report, not a pass.
- **Measure what can be measured** before and after.
- **Never call an item passed from the code alone,** or from a record that
  already existed. Make one.
- **A guard that fails is the item failing.** Changing a guard is the
  user's decision.
- **The browser suite is not a gate.** Run one spec by name when asked.
- **Stop at the end of the list.** A pass that keeps finding scope is two
  passes; finish this one and say what the next is.

## Claude's passthrough habits, and what to do instead

- **Calling it done after the desktop in English.** Phone, Arabic and dark
  find a third of the problems.
- **Fixing the symptom on one screen.** Fix the part that draws it.
- **Trusting the guards for completeness.** They hold what is declared; an
  action with no card, an event with no notification and a record type with
  no icons all pass them.
- **Forgetting the paperwork**: an old Help picture, no version, no
  translation, no stamp.
- **Adding a mechanism and not a line here.** A new registry, centre or
  guard every app must answer goes into **What a pass looks at**, in the
  same commit.
- **Turning a pass into a redesign.** What the user did not ask for goes
  to them as a question.

## Finishing

Every item is stamped, or listed as not passed with the reason. Run the
gates, about a minute apart:

    python3 scripts/quick.py --all                                        # every test
    bench --site <dev site> execute onedesk.one_demo.check.run            # the demo, as its people
    python3 scripts/overrides.py --check && python3 scripts/docs.py --check
    cd frontend && npx vitest run && npx eslint src && npx vite build    # when frontend source changed

READY.md's **The gates** is the full list. A test that failed before this
pass is named in the report, not hidden and not fixed in its commit.

Report in one or two sentences: the scope, how many items passed, the one
thing left open. The commit messages carry the detail.
